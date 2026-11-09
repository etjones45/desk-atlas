// Car Atlas backend: car.etjarvis.com
// - App login (household password) with long-lived sessions
// - Pi endpoints (device key from pairing): status, coverage, clips, alerts, commands
// - Web push to phones that turned on notifications
import { sendPush, b64u, unb64u } from "./push.js";

const enc = new TextEncoder();
const now = () => Date.now() / 1000;
const SESSION_DAYS = 180;
// Version of this web app + server. Bump together with car/VERSION on every release.
const APP_VERSION = "1.1";
const REPO_RAW = "https://raw.githubusercontent.com/etjones45/desk-atlas/car/car";
const COMMANDS = {
  upload_recent: "Upload recent dashcam",
  restart_dish: "Restart Starlink",
  update_now: "Check for Pi updates",
  restart_services: "Restart Pi services",
  reboot_pi: "Restart the Pi",
  test_alert: "Send a test alert from the Pi",
  usb_rebind: "Re-offer the dashcam drive",
  usb_fix: "Switch USB0 to fallback mode",
  usb_fix_undo: "Undo the USB0 fallback",
};

// ---------- helpers ----------
function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store", ...headers },
  });
}
const err = (status, message) => json({ error: message }, status);

async function sha256hex(text) {
  const d = await crypto.subtle.digest("SHA-256", enc.encode(text));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function randomToken(n = 32) {
  return b64u(crypto.getRandomValues(new Uint8Array(n)));
}
function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}
async function pbkdf2(password, saltB64, iterations) {
  const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt: unb64u(saltB64), iterations }, key, 256);
  return b64u(bits);
}
async function hashPassword(password) {
  const salt = b64u(crypto.getRandomValues(new Uint8Array(16)));
  return `pbkdf2$25000$${salt}$${await pbkdf2(password, salt, 25000)}`;
}
async function checkPassword(password, stored) {
  if (!stored) return false;
  const [, iters, salt, hash] = stored.split("$");
  return safeEqual(await pbkdf2(password, salt, Number(iters)), hash);
}
async function kvGet(env, k) {
  const r = await env.DB.prepare("SELECT v FROM kv WHERE k=?").bind(k).first();
  return r ? r.v : null;
}
async function kvSet(env, k, v) {
  await env.DB.prepare("INSERT INTO kv(k,v,updated) VALUES(?,?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v, updated=excluded.updated")
    .bind(k, v, now()).run();
}
function cookie(req, name) {
  const c = req.headers.get("Cookie") || "";
  for (const part of c.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return v.join("=");
  }
  return null;
}
async function readJson(req) {
  const ct = req.headers.get("Content-Type") || "";
  if (!ct.includes("application/json")) throw new Error("Expected JSON");
  return await req.json();
}
const num = (v) => (v === null || v === undefined || v === "" || isNaN(Number(v)) ? null : Number(v));
const dayOf = (ts) => new Date(ts * 1000).toLocaleDateString("en-CA", { timeZone: "America/Denver" });

// ---------- versions ----------
// Compare "1.10" vs "1.9" the way people expect. Returns -1, 0, 1 (null if either is missing).
function cmpVersion(a, b) {
  if (!a || !b) return null;
  const pa = String(a).split(".").map((x) => parseInt(x, 10) || 0);
  const pb = String(b).split(".").map((x) => parseInt(x, 10) || 0);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const d = (pa[i] || 0) - (pb[i] || 0);
    if (d) return d > 0 ? 1 : -1;
  }
  return 0;
}
// Newest released version = car/VERSION on the GitHub branch the Pi updates from. Cached ~10 min.
async function latestVersion(env, ctx, force = false) {
  const cached = await kvGet(env, "latest_version");
  const at = Number(await kvGet(env, "latest_version_at")) || 0;
  if (!force && cached && now() - at < 600) return { version: cached, checked_at: at };
  const refresh = (async () => {
    try {
      const r = await fetch(`${REPO_RAW}/VERSION?t=${Math.floor(now() / 120)}`, { cf: { cacheTtlByStatus: { "200-299": 120, "404": 0, "500-599": 0 } } });
      if (!r.ok) throw new Error(`GitHub ${r.status}`);
      const v = (await r.text()).trim();
      if (!/^\d+(\.\d+){0,3}$/.test(v)) throw new Error("bad VERSION");
      await kvSet(env, "latest_version", v);
      await kvSet(env, "latest_version_at", String(now()));
      return { version: v, checked_at: now() };
    } catch (e) {
      return { version: cached || null, checked_at: at || null, error: String(e.message || e) };
    }
  })();
  // Serve the cached answer right away when we have one; refresh in the background.
  if (cached && !force && ctx) { ctx.waitUntil(refresh); return { version: cached, checked_at: at }; }
  return await refresh;
}
function versionInfo(status, statusAt, latest) {
  const pi = status ? (status.pi?.version || "1.0") : null; // builds before 1.1 didn't report a version
  const cmpPi = cmpVersion(pi, latest.version);
  let state = "unknown";
  if (pi && latest.version) state = cmpPi === 0 ? "current" : cmpPi < 0 ? "behind" : "ahead";
  return {
    app: APP_VERSION,
    latest: latest.version,
    latest_checked_at: latest.checked_at,
    latest_error: latest.error || null,
    pi,
    pi_sha: status?.pi?.code_version || null,
    pi_update: status?.pi?.update || null,
    pi_reported_at: statusAt,
    pi_state: state,
    app_state: latest.version ? (cmpVersion(APP_VERSION, latest.version) >= 0 ? "current" : "behind") : "unknown",
  };
}
// Where is the car? Prefer what the Pi reports now (USB GPS / dish), else the last logged point.
function carLocation(status, statusAt, lastRow) {
  const l = status?.location;
  if (l && num(l.lat) !== null && num(l.lon) !== null) {
    return { ts: num(l.at) || statusAt, lat: num(l.lat), lon: num(l.lon), source: l.source || null,
      stale: !!l.stale, speed_mph: num(l.speed_mph) };
  }
  return lastRow ? { ...lastRow, source: "history", stale: true } : null;
}

// ---------- auth ----------
async function sessionFrom(req, env) {
  const id = cookie(req, "ca_s");
  if (!id) return null;
  const row = await env.DB.prepare("SELECT id, expires FROM sessions WHERE id=?").bind(await sha256hex(id)).first();
  if (!row || row.expires < now()) return null;
  return row;
}
async function deviceFrom(req, env) {
  const h = req.headers.get("Authorization") || "";
  if (!h.startsWith("Bearer ")) return false;
  const stored = await kvGet(env, "device_key_hash");
  return !!stored && safeEqual(await sha256hex(h.slice(7).trim()), stored);
}

// ---------- push fan-out ----------
async function notifyAll(env, payload, category, ctx) {
  const subs = (await env.DB.prepare("SELECT * FROM push_subs").all()).results || [];
  const work = subs.map(async (s) => {
    const prefs = JSON.parse(s.prefs || "{}");
    if (category && prefs[category] === false) return null;
    try {
      const status = await sendPush(env, s, payload);
      if (status === 404 || status === 410) {
        await env.DB.prepare("DELETE FROM push_subs WHERE endpoint=?").bind(s.endpoint).run();
      } else if (status < 300) {
        await env.DB.prepare("UPDATE push_subs SET last_ok=? WHERE endpoint=?").bind(now(), s.endpoint).run();
      }
      return { label: s.label, status };
    } catch (e) {
      return { label: s.label, error: String(e) };
    }
  });
  const all = Promise.all(work);
  if (ctx) ctx.waitUntil(all);
  return all;
}
async function addAlert(env, ctx, { title, message, category = "info", link = null }) {
  await env.DB.prepare("INSERT INTO alerts(at,title,message,category,link) VALUES(?,?,?,?,?)")
    .bind(now(), String(title).slice(0, 120), String(message || "").slice(0, 400), category, link).run();
  notifyAll(env, { title, body: message, url: link || "/#home", tag: category }, category, ctx);
}

// ---------- app API ----------
async function overview(env, ctx) {
  const latest = await kvGet(env, "latest");
  const latestAt = Number(await kvGet(env, "latest_at")) || null;
  const clips = (await env.DB.prepare(
    "SELECT id, kind, folder, drive_url, size_mb, reason, city, lat, lon, event_ts, uploaded_at, network, thumb IS NOT NULL AS has_thumb FROM clips ORDER BY uploaded_at DESC LIMIT 8").all()).results;
  const alerts = (await env.DB.prepare("SELECT * FROM alerts ORDER BY at DESC LIMIT 15").all()).results;
  const commands = (await env.DB.prepare("SELECT * FROM commands ORDER BY created DESC LIMIT 8").all()).results;
  const counts = await env.DB.prepare(
    "SELECT SUM(kind='dashcam') AS dashcam, SUM(kind='sentry') AS sentry, SUM(kind='requested') AS requested, COALESCE(SUM(size_mb),0) AS total_mb FROM clips").first();
  const today = await env.DB.prepare("SELECT * FROM usage_daily WHERE day=?").bind(dayOf(now())).first();
  const lastLoc = await env.DB.prepare("SELECT ts, lat, lon FROM history WHERE lat IS NOT NULL ORDER BY ts DESC LIMIT 1").first();
  const status = latest ? JSON.parse(latest) : null;
  const latestV = await latestVersion(env, ctx);
  return {
    server_time: now(),
    app_version: APP_VERSION,
    versions: versionInfo(status, latestAt, latestV),
    status,
    status_at: latestAt,
    paired: !!(await kvGet(env, "device_key_hash")),
    paired_at: Number(await kvGet(env, "paired_at")) || null,
    clips, alerts, commands, counts, today, last_location: carLocation(status, latestAt, lastLoc),
    command_labels: COMMANDS,
  };
}

async function history(env, url) {
  const hours = Math.min(Math.max(Number(url.searchParams.get("hours")) || 24, 1), 24 * 60);
  const rows = (await env.DB.prepare("SELECT * FROM history WHERE ts > ? ORDER BY ts").bind(now() - hours * 3600).all()).results;
  const maxPts = 600;
  if (rows.length <= maxPts) return { hours, rows };
  const step = Math.ceil(rows.length / maxPts);
  return { hours, rows: rows.filter((_, i) => i % step === 0 || i === rows.length - 1) };
}

async function handleApp(req, env, ctx, url, path) {
  const m = req.method;
  if (path === "/api/overview" && m === "GET") return json(await overview(env, ctx));
  if (path === "/api/version" && m === "GET") {
    const latest = await kvGet(env, "latest");
    const at = Number(await kvGet(env, "latest_at")) || null;
    const lv = await latestVersion(env, ctx, url.searchParams.get("refresh") === "1");
    return json(versionInfo(latest ? JSON.parse(latest) : null, at, lv));
  }
  if (path === "/api/changelog" && m === "GET") {
    let text = await kvGet(env, "changelog");
    const at = Number(await kvGet(env, "changelog_at")) || 0;
    if (!text || now() - at > 3600) {
      try {
        const r = await fetch(`${REPO_RAW}/CHANGELOG.md?t=${Math.floor(now() / 600)}`, { cf: { cacheTtlByStatus: { "200-299": 600, "404": 0, "500-599": 0 } } });
        if (r.ok) {
          text = (await r.text()).slice(0, 20000);
          await kvSet(env, "changelog", text);
          await kvSet(env, "changelog_at", String(now()));
        }
      } catch { /* keep the cached copy */ }
    }
    return json({ text: text || "" });
  }
  if (path === "/api/clip-pins" && m === "GET") {
    const days = Math.min(Number(url.searchParams.get("days")) || 90, 365);
    const rows = (await env.DB.prepare(
      "SELECT id, kind, folder, drive_url, reason, city, lat, lon, event_ts, uploaded_at FROM clips WHERE lat IS NOT NULL AND lon IS NOT NULL AND uploaded_at > ? ORDER BY uploaded_at DESC LIMIT 500")
      .bind(now() - days * 86400).all()).results;
    return json({ days, pins: rows });
  }
  if (path === "/api/history" && m === "GET") return json(await history(env, url));
  if (path === "/api/usage" && m === "GET") {
    const days = Math.min(Number(url.searchParams.get("days")) || 30, 365);
    const rows = (await env.DB.prepare("SELECT * FROM usage_daily ORDER BY day DESC LIMIT ?").bind(days).all()).results;
    return json({ rows: rows.reverse() });
  }
  if (path === "/api/coverage" && m === "GET") {
    const days = Math.min(Number(url.searchParams.get("days")) || 30, 365);
    const rows = (await env.DB.prepare("SELECT ts, lat, lon, q, ping, drop_pct FROM coverage WHERE ts > ? ORDER BY ts LIMIT 30000")
      .bind(now() - days * 86400).all()).results;
    return json({ days, points: rows.map((r) => [r.ts, r.lat, r.lon, r.q, r.ping, r.drop_pct]) });
  }
  if (path === "/api/clips" && m === "GET") {
    const kind = url.searchParams.get("kind") || "all";
    const before = Number(url.searchParams.get("before")) || 1e15;
    const limit = Math.min(Number(url.searchParams.get("limit")) || 30, 100);
    const q = kind === "all"
      ? env.DB.prepare("SELECT id, kind, folder, drive_url, size_mb, reason, city, lat, lon, event_ts, uploaded_at, network, thumb IS NOT NULL AS has_thumb FROM clips WHERE id < ? ORDER BY id DESC LIMIT ?").bind(before, limit)
      : env.DB.prepare("SELECT id, kind, folder, drive_url, size_mb, reason, city, lat, lon, event_ts, uploaded_at, network, thumb IS NOT NULL AS has_thumb FROM clips WHERE kind=? AND id < ? ORDER BY id DESC LIMIT ?").bind(kind, before, limit);
    return json({ clips: (await q.all()).results });
  }
  const thumb = path.match(/^\/api\/clips\/(\d+)\/thumb$/);
  if (thumb && m === "GET") {
    const r = await env.DB.prepare("SELECT thumb, thumb_type FROM clips WHERE id=?").bind(Number(thumb[1])).first();
    if (!r || !r.thumb) return err(404, "No thumbnail");
    return new Response(new Uint8Array(r.thumb), { headers: { "Content-Type": r.thumb_type || "image/png", "Cache-Control": "private, max-age=86400" } });
  }
  if (path === "/api/commands" && m === "GET") {
    return json({ commands: (await env.DB.prepare("SELECT * FROM commands ORDER BY created DESC LIMIT 20").all()).results, labels: COMMANDS });
  }
  if (path === "/api/commands" && m === "POST") {
    const b = await readJson(req);
    if (!COMMANDS[b.type]) return err(400, "Unknown action");
    const args = b.type === "upload_recent" ? { minutes: Math.max(1, Math.min(60, Number(b.args?.minutes) || 10)) } : {};
    const open = await env.DB.prepare("SELECT id FROM commands WHERE type=? AND status IN ('queued','picked')").bind(b.type).first();
    if (open) return json({ ok: true, id: open.id, note: "Already waiting for the Pi" });
    const r = await env.DB.prepare("INSERT INTO commands(type,args,status,created) VALUES(?,?,'queued',?)")
      .bind(b.type, JSON.stringify(args), now()).run();
    return json({ ok: true, id: r.meta.last_row_id });
  }
  if (path === "/api/commands/cancel" && m === "POST") {
    const b = await readJson(req);
    await env.DB.prepare("UPDATE commands SET status='cancelled', done=? WHERE id=? AND status='queued'").bind(now(), Number(b.id)).run();
    return json({ ok: true });
  }
  if (path === "/api/push/subscribe" && m === "POST") {
    const b = await readJson(req);
    if (!b.endpoint || !b.keys?.p256dh || !b.keys?.auth) return err(400, "Bad subscription");
    await env.DB.prepare("INSERT INTO push_subs(endpoint,p256dh,auth,label,created,prefs) VALUES(?,?,?,?,?,?) ON CONFLICT(endpoint) DO UPDATE SET p256dh=excluded.p256dh, auth=excluded.auth, label=excluded.label")
      .bind(b.endpoint, b.keys.p256dh, b.keys.auth, String(b.label || "Phone").slice(0, 40), now(), JSON.stringify({ clip: true, problem: true, info: true })).run();
    return json({ ok: true });
  }
  if (path === "/api/push/unsubscribe" && m === "POST") {
    const b = await readJson(req);
    await env.DB.prepare("DELETE FROM push_subs WHERE endpoint=?").bind(String(b.endpoint || "")).run();
    return json({ ok: true });
  }
  if (path === "/api/push/prefs" && m === "POST") {
    const b = await readJson(req);
    const prefs = { clip: b.prefs?.clip !== false, problem: b.prefs?.problem !== false, info: b.prefs?.info !== false };
    await env.DB.prepare("UPDATE push_subs SET prefs=? WHERE endpoint=?").bind(JSON.stringify(prefs), String(b.endpoint || "")).run();
    return json({ ok: true, prefs });
  }
  if (path === "/api/push/status" && m === "POST") {
    const b = await readJson(req);
    const r = await env.DB.prepare("SELECT label, prefs, last_ok FROM push_subs WHERE endpoint=?").bind(String(b.endpoint || "")).first();
    const n = await env.DB.prepare("SELECT COUNT(*) AS n FROM push_subs").first();
    return json({ subscribed: !!r, prefs: r ? JSON.parse(r.prefs || "{}") : null, devices: n.n });
  }
  if (path === "/api/push/test" && m === "POST") {
    const results = await notifyAll(env, { title: "Car Atlas", body: "Notifications are working. 🚗📡", url: "/#home", tag: "test" }, null, null);
    return json({ results });
  }
  if (path === "/api/settings/password" && m === "POST") {
    const b = await readJson(req);
    if (!(await checkPassword(String(b.current || ""), await kvGet(env, "pw_hash")))) return err(403, "Current password is wrong");
    if (String(b.next || "").length < 8) return err(400, "New password needs at least 8 characters");
    await kvSet(env, "pw_hash", await hashPassword(String(b.next)));
    return json({ ok: true });
  }
  if (path === "/api/pairing-code" && m === "POST") {
    const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
    const bytes = crypto.getRandomValues(new Uint8Array(8));
    let code = "";
    bytes.forEach((b, i) => { code += alphabet[b % alphabet.length]; if (i === 3) code += "-"; });
    await env.DB.prepare("INSERT INTO pairing(code, expires, used) VALUES(?,?,0)").bind(code, now() + 1800).run();
    return json({ code, expires: now() + 1800 });
  }
  if (path === "/api/sessions/logout-all" && m === "POST") {
    await env.DB.prepare("DELETE FROM sessions").run();
    return json({ ok: true }, 200, { "Set-Cookie": "ca_s=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax" });
  }
  return err(404, "Not found");
}

// ---------- Pi API ----------
async function handlePi(req, env, ctx, path) {
  const m = req.method;
  if (path === "/api/pi/status" && m === "POST") {
    const s = await readJson(req);
    const t = now();
    await kvSet(env, "latest", JSON.stringify(s));
    await kvSet(env, "latest_at", String(t));
    const last = await env.DB.prepare("SELECT MAX(ts) AS ts FROM history").first();
    if (!last.ts || t - last.ts >= 50) {
      const pi = s.pi || {}, d = s.starlink || {}, cam = s.teslacam || {};
      const loc = (s.location && !s.location.stale ? s.location : null) || d.location || {};
      await env.DB.prepare(`INSERT OR REPLACE INTO history(ts, net, internet, dish_ok, state, quality, ping, drop_pct, obstructed, down, up, power, temp, load1, wifi_signal, gadget, usb_link, lat, lon)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(
        t, pi.network || null, pi.internet ? 1 : 0, d.reachable ? 1 : 0, d.state || null, d.quality || null,
        num(d.ping_ms), num(d.drop_pct), num(d.obstructed_pct), num(d.down_mbps), num(d.up_mbps), num(d.power_w),
        num(pi.cpu_temp_c), num(pi.load1), num(pi.wifi_signal), cam.gadget || null, cam.usb_link || null,
        num(loc.lat), num(loc.lon)).run();
    }
    const u = s.starlink?.usage_today_mb;
    if (u) {
      await env.DB.prepare(`INSERT INTO usage_daily(day, down_mb, up_mb, clips_mb) VALUES(?,?,?,?) ON CONFLICT(day) DO UPDATE SET
        down_mb=MAX(down_mb, excluded.down_mb), up_mb=MAX(up_mb, excluded.up_mb), clips_mb=MAX(COALESCE(clips_mb,0), excluded.clips_mb)`)
        .bind(dayOf(t), num(u.down) || 0, num(u.up) || 0, num(s.teslacam?.starlink_uploaded_today_mb) || 0).run();
    }
    const pending = await env.DB.prepare("SELECT COUNT(*) AS n FROM commands WHERE status='queued'").first();
    const lv = await latestVersion(env, ctx);
    return json({ ok: true, commands_waiting: pending.n, latest_version: lv.version });
  }
  if (path === "/api/pi/coverage" && m === "POST") {
    const b = await readJson(req);
    const pts = (b.points || []).slice(0, 2000);
    const stmts = pts.filter((p) => num(p[1]) !== null && num(p[2]) !== null).map((p) =>
      env.DB.prepare("INSERT OR IGNORE INTO coverage(ts,lat,lon,q,ping,drop_pct) VALUES(?,?,?,?,?,?)")
        .bind(num(p[0]), num(p[1]), num(p[2]), String(p[3] || "g").slice(0, 1), num(p[4]), num(p[5])));
    for (let i = 0; i < stmts.length; i += 100) await env.DB.batch(stmts.slice(i, i + 100));
    return json({ ok: true, saved: stmts.length });
  }
  if (path === "/api/pi/clip" && m === "POST") {
    const c = await readJson(req);
    const kind = ["dashcam", "sentry", "requested"].includes(c.kind) ? c.kind : "dashcam";
    let thumb = null;
    if (c.thumb_b64 && c.thumb_b64.length < 700000) {
      try { thumb = Uint8Array.from(atob(c.thumb_b64), (ch) => ch.charCodeAt(0)); } catch { thumb = null; }
    }
    const driveUrl = c.drive_id ? `https://drive.google.com/drive/folders/${c.drive_id}` : (c.drive_url || null);
    await env.DB.prepare(`INSERT INTO clips(kind, folder, drive_id, drive_url, size_mb, reason, city, lat, lon, event_ts, uploaded_at, network, thumb, thumb_type)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(kind, folder) DO UPDATE SET drive_id=excluded.drive_id, drive_url=excluded.drive_url,
      size_mb=excluded.size_mb, uploaded_at=excluded.uploaded_at, thumb=COALESCE(excluded.thumb, clips.thumb)`).bind(
      kind, String(c.folder).slice(0, 80), c.drive_id || null, driveUrl, num(c.size_mb), c.reason || null, c.city || null,
      num(c.lat), num(c.lon), c.event_ts || null, now(), c.network || null, thumb, c.thumb_type || "image/png").run();
    const label = kind === "sentry" ? "Sentry event saved" : kind === "requested" ? "Your dashcam request is ready" : "Dashcam clip saved";
    const where = c.city ? ` in ${c.city}` : "";
    await addAlert(env, ctx, { title: label, message: `${c.folder}${where} is in Google Drive.`, category: "clip", link: "/#footage" });
    return json({ ok: true });
  }
  if (path === "/api/pi/alert" && m === "POST") {
    const a = await readJson(req);
    await addAlert(env, ctx, { title: a.title || "Car Atlas", message: a.message || "", category: ["clip", "problem", "info"].includes(a.category) ? a.category : "info", link: a.link || "/#home" });
    return json({ ok: true });
  }
  if (path === "/api/pi/commands" && m === "GET") {
    const rows = (await env.DB.prepare("SELECT id, type, args FROM commands WHERE status='queued' ORDER BY created LIMIT 5").all()).results;
    for (const r of rows) await env.DB.prepare("UPDATE commands SET status='picked', picked=? WHERE id=?").bind(now(), r.id).run();
    return json({ commands: rows.map((r) => ({ ...r, args: JSON.parse(r.args || "{}") })) });
  }
  const done = path.match(/^\/api\/pi\/commands\/(\d+)$/);
  if (done && m === "POST") {
    const b = await readJson(req);
    await env.DB.prepare("UPDATE commands SET status=?, done=?, result=? WHERE id=?")
      .bind(b.ok ? "done" : "failed", now(), String(b.result || "").slice(0, 500), Number(done[1])).run();
    return json({ ok: true });
  }
  return err(404, "Not found");
}

// ---------- entry ----------
export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const path = url.pathname;
    if (!path.startsWith("/api/")) return env.ASSETS.fetch(req);
    try {
      if (path === "/api/health") return json({ ok: true, time: now(), version: APP_VERSION });

      if (path === "/api/login" && req.method === "POST") {
        const ip = req.headers.get("CF-Connecting-IP") || "unknown";
        const recent = await env.DB.prepare("SELECT COUNT(*) AS n FROM login_attempts WHERE ip=? AND ts>?").bind(ip, now() - 900).first();
        if (recent.n >= 8) return err(429, "Too many tries. Wait 15 minutes and try again.");
        const b = await readJson(req);
        if (!(await checkPassword(String(b.password || ""), await kvGet(env, "pw_hash")))) {
          await env.DB.prepare("INSERT INTO login_attempts(ip, ts) VALUES(?,?)").bind(ip, now()).run();
          return err(403, "That password didn't work.");
        }
        const id = randomToken();
        await env.DB.prepare("INSERT INTO sessions(id, created, expires, label) VALUES(?,?,?,?)")
          .bind(await sha256hex(id), now(), now() + SESSION_DAYS * 86400, String(b.label || "").slice(0, 40)).run();
        return json({ ok: true }, 200, { "Set-Cookie": `ca_s=${id}; Path=/; Max-Age=${SESSION_DAYS * 86400}; HttpOnly; Secure; SameSite=Lax` });
      }
      if (path === "/api/logout" && req.method === "POST") {
        const id = cookie(req, "ca_s");
        if (id) await env.DB.prepare("DELETE FROM sessions WHERE id=?").bind(await sha256hex(id)).run();
        return json({ ok: true }, 200, { "Set-Cookie": "ca_s=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax" });
      }
      if (path === "/api/pair" && req.method === "POST") {
        const b = await readJson(req);
        const code = String(b.code || "").toUpperCase().trim();
        const row = await env.DB.prepare("SELECT * FROM pairing WHERE code=?").bind(code).first();
        if (!row || row.used || row.expires < now()) return err(403, "That pairing code is wrong or expired. Make a new one in the app.");
        const key = randomToken(32);
        await env.DB.prepare("UPDATE pairing SET used=1 WHERE code=?").bind(code).run();
        await kvSet(env, "device_key_hash", await sha256hex(key));
        await kvSet(env, "paired_at", String(now()));
        await addAlert(env, ctx, { title: "Pi connected", message: `${b.hostname || "The Pi"} is now linked to Car Atlas.`, category: "info" });
        return json({ ok: true, key, url: `${url.protocol}//${url.host}` });
      }
      if (path.startsWith("/api/pi/")) {
        if (!(await deviceFrom(req, env))) return err(401, "Device not paired");
        return await handlePi(req, env, ctx, path);
      }
      const sess = await sessionFrom(req, env);
      if (path === "/api/me") return json({ authed: !!sess, vapid_public: env.VAPID_PUBLIC, app_version: APP_VERSION });
      if (!sess) return err(401, "Please log in");
      return await handleApp(req, env, ctx, url, path);
    } catch (e) {
      return err(e.message === "Expected JSON" ? 415 : 500, e.message === "Expected JSON" ? "Expected JSON" : "Something went wrong: " + String(e.message || e).slice(0, 200));
    }
  },

  async scheduled(event, env) {
    const t = now();
    await env.DB.batch([
      env.DB.prepare("DELETE FROM history WHERE ts < ?").bind(t - 120 * 86400),
      env.DB.prepare("DELETE FROM login_attempts WHERE ts < ?").bind(t - 86400),
      env.DB.prepare("DELETE FROM sessions WHERE expires < ?").bind(t),
      env.DB.prepare("DELETE FROM pairing WHERE expires < ?").bind(t - 86400),
      env.DB.prepare("DELETE FROM commands WHERE created < ?").bind(t - 30 * 86400),
      env.DB.prepare("DELETE FROM alerts WHERE id NOT IN (SELECT id FROM alerts ORDER BY at DESC LIMIT 500)"),
      env.DB.prepare("UPDATE commands SET status='expired' WHERE status='queued' AND created < ?").bind(t - 86400),
    ]);
  },
};
