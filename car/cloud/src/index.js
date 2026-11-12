// Car Atlas backend: car.etjarvis.com
// - App login (household password) with long-lived sessions
// - Pi endpoints (device key from pairing): status, coverage, clips, alerts, commands
// - Web push to phones that turned on notifications
import { sendPush, b64u, unb64u } from "./push.js";

const enc = new TextEncoder();
const now = () => Date.now() / 1000;
const SESSION_DAYS = 180;
// Version of this web app + server. Bump together with car/VERSION on every release.
const APP_VERSION = "1.2.7";
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
  speedtest: "Speed test",
  doctor: "Health check",
  usb_debug: "USB deep check",
  logs: "Recent logs",
  sysinfo: "What the Pi is busy with",
};
// What the app can tell the Pi to do differently. The Pi picks these up at every check-in.
const PI_SETTINGS = {
  uploads_paused: { type: "bool", def: false },
  uploads_on_starlink: { type: "bool", def: true },
  sentry_on_starlink: { type: "bool", def: true },
  starlink_cap_mb: { type: "int", def: 5000, min: 0, max: 100000 },
  starlink_speed: { type: "enum", def: "normal", values: ["slow", "normal", "fast", "max"] },
  auto_speedtest: { type: "bool", def: true },
  retention_days: { type: "enum", def: 0, values: [0, 30, 60, 90, 180, 365] },
  heat_protect: { type: "bool", def: true },
  plan_protect: { type: "bool", def: true },
  plan_gb: { type: "int", def: 0, min: 0, max: 10000 },       // 0 = no monthly limit set
  plan_reset_day: { type: "int", def: 1, min: 1, max: 28 },
};
const CMD_COLS = "id, type, args, status, created, picked, done, result, output IS NOT NULL AS has_output";
const PUSH_DEFAULTS = { clip: true, problem: true, info: true, recap: true, wake: false, online: false };

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
function denverClock(ts) {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: "America/Denver", hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" })
    .formatToParts(new Date(ts * 1000));
  const g = (t) => Number(parts.find((p) => p.type === t)?.value || 0);
  return { h: g("hour") % 24, m: g("minute"), s: g("second") };
}
const denverMidnight = (ts) => { const c = denverClock(ts); return ts - (c.h * 3600 + c.m * 60 + c.s); };
const clockText = (ts) => new Date(ts * 1000).toLocaleTimeString("en-US", { timeZone: "America/Denver", hour: "numeric", minute: "2-digit" });
function durText(sec) {
  sec = Math.max(0, Math.round(sec || 0));
  const h = Math.floor(sec / 3600), m = Math.round((sec % 3600) / 60);
  return h ? `${h}h ${m}m` : m ? `${m} min` : `${sec} sec`;
}

// ---------- Pi settings + data plan ----------
async function piSettings(env) {
  let saved = {};
  try { saved = JSON.parse((await kvGet(env, "pi_settings")) || "{}"); } catch { saved = {}; }
  const out = {};
  for (const [k, spec] of Object.entries(PI_SETTINGS)) out[k] = saved[k] === undefined ? spec.def : saved[k];
  out.rev = Number(saved.rev) || 0;
  return out;
}
function cleanSetting(key, value) {
  const spec = PI_SETTINGS[key];
  if (!spec) return undefined;
  if (spec.type === "bool") return !!value;
  if (spec.type === "int") { const n = Math.round(Number(value)); return isNaN(n) ? undefined : Math.max(spec.min, Math.min(spec.max, n)); }
  if (spec.type === "enum") { const v = typeof spec.def === "number" ? Number(value) : String(value); return spec.values.includes(v) ? v : undefined; }
  return undefined;
}
// This month's Starlink data against the plan limit (if one is set in the app).
async function planUsage(env, st) {
  if (!st.plan_gb) return null;
  const t = now();
  let start = denverMidnight(t), startDay = dayOf(t);
  for (let i = 0; i < 32; i++) {
    const d = dayOf(start + 3600);
    if (Number(d.slice(8, 10)) === st.plan_reset_day) { startDay = d; break; }
    start -= 86400;
  }
  const r = await env.DB.prepare("SELECT COALESCE(SUM(COALESCE(down_mb,0)+COALESCE(up_mb,0)),0) AS mb FROM usage_daily WHERE day >= ?").bind(startDay).first();
  const used = (r.mb || 0) / 1000;
  const daysIn = Math.max(1, Math.round((t - start) / 86400) + 1);
  return { gb: st.plan_gb, reset_day: st.plan_reset_day, cycle_start: startDay, used_gb: Math.round(used * 10) / 10,
    pct: Math.round((100 * used) / st.plan_gb), days_in: daysIn, per_day_gb: Math.round((used / daysIn) * 10) / 10 };
}

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
    let prefs = {};
    try { prefs = JSON.parse(s.prefs || "{}"); } catch { prefs = {}; }
    if (category) {
      const on = prefs[category] === undefined ? PUSH_DEFAULTS[category] !== false : !!prefs[category];
      if (!on) return null;
      // Quiet hours hold everything except problems.
      if (category !== "problem" && prefs.quiet && prefs.quiet.on) {
        const h = denverClock(now()).h, a = Number(prefs.quiet.from ?? 22), b = Number(prefs.quiet.to ?? 7);
        if (a === b || (a < b ? h >= a && h < b : h >= a || h < b)) return null;
      }
    }
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
async function addAlert(env, ctx, { title, message, category = "info", link = null, at = null, push = true }) {
  const t = now();
  const when = at && at <= t + 60 && at > t - 4 * 86400 ? at : t;
  await env.DB.prepare("INSERT INTO alerts(at,title,message,category,link) VALUES(?,?,?,?,?)")
    .bind(when, String(title).slice(0, 120), String(message || "").slice(0, 400), category, link).run();
  // Something that happened a while ago (the Pi was offline) goes in the list but doesn't buzz the phone late.
  if (push && t - when < 1800) {
    const p = notifyAll(env, { title, body: message, url: link || "/#home", tag: category }, category, ctx);
    if (!ctx) await p;
  }
}

// ---------- app API ----------
async function overview(env, ctx) {
  const latest = await kvGet(env, "latest");
  const latestAt = Number(await kvGet(env, "latest_at")) || null;
  const clips = (await env.DB.prepare(
    "SELECT id, kind, folder, drive_url, size_mb, reason, city, lat, lon, event_ts, uploaded_at, network, camera, files, encrypted, thumb IS NOT NULL AS has_thumb FROM clips ORDER BY uploaded_at DESC LIMIT 8").all()).results;
  const alerts = (await env.DB.prepare("SELECT * FROM alerts ORDER BY at DESC LIMIT 15").all()).results;
  const commands = (await env.DB.prepare(`SELECT ${CMD_COLS} FROM commands ORDER BY created DESC LIMIT 10`).all()).results;
  const counts = await env.DB.prepare(
    "SELECT SUM(kind='dashcam') AS dashcam, SUM(kind='sentry') AS sentry, SUM(kind='requested') AS requested, COALESCE(SUM(size_mb),0) AS total_mb FROM clips").first();
  const today = await env.DB.prepare("SELECT * FROM usage_daily WHERE day=?").bind(dayOf(now())).first();
  const lastLoc = await env.DB.prepare("SELECT ts, lat, lon FROM history WHERE lat IS NOT NULL ORDER BY ts DESC LIMIT 1").first();
  const status = latest ? JSON.parse(latest) : null;
  const latestV = await latestVersion(env, ctx);
  const t = now(), mid = denverMidnight(t);
  const st = await piSettings(env);
  const drops = await env.DB.prepare("SELECT COUNT(*) AS n, COALESCE(SUM(end - start),0) AS s FROM outages WHERE start >= ?").bind(mid).first();
  const clipsToday = await env.DB.prepare("SELECT COUNT(*) AS n FROM clips WHERE uploaded_at >= ?").bind(mid).first();
  const speed = await env.DB.prepare("SELECT * FROM speedtests ORDER BY at DESC LIMIT 1").first();
  const week = await env.DB.prepare(`SELECT COALESCE(SUM(awake_s),0) AS awake_s, COALESCE(SUM(starlink_s),0) AS starlink_s, COALESCE(SUM(good_s),0) AS good_s,
    COALESCE(SUM(COALESCE(down_mb,0)+COALESCE(up_mb,0)),0) AS data_mb, COALESCE(SUM(energy_wh),0) AS energy_wh FROM usage_daily WHERE day >= ?`).bind(dayOf(t - 6 * 86400)).first();
  const weekDrops = await env.DB.prepare("SELECT COUNT(*) AS n FROM outages WHERE start >= ?").bind(t - 7 * 86400).first();
  let sess = null;
  try { sess = JSON.parse((await kvGet(env, "sess")) || "null"); } catch { sess = null; }
  return {
    settings: st,
    settings_applied: status ? status.settings_rev === st.rev : null,
    plan: await planUsage(env, st),
    drops_today: { count: drops.n, seconds: Math.round(drops.s) },
    clips_today: clipsToday.n,
    speedtest_last: speed || null,
    week: { ...week, drops: weekDrops.n },
    session: sess && latestAt && t - sess.last < 600 ? { start: sess.start, last: sess.last } : null,
    wifi_set: !!(await kvGet(env, "wifi")),
    shortcut_set: !!(await kvGet(env, "shortcut_key_hash")),
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
      ? env.DB.prepare("SELECT id, kind, folder, drive_url, size_mb, reason, city, lat, lon, event_ts, uploaded_at, network, camera, files, encrypted, thumb IS NOT NULL AS has_thumb FROM clips WHERE id < ? ORDER BY id DESC LIMIT ?").bind(before, limit)
      : env.DB.prepare("SELECT id, kind, folder, drive_url, size_mb, reason, city, lat, lon, event_ts, uploaded_at, network, camera, files, encrypted, thumb IS NOT NULL AS has_thumb FROM clips WHERE kind=? AND id < ? ORDER BY id DESC LIMIT ?").bind(kind, before, limit);
    return json({ clips: (await q.all()).results });
  }
  const thumb = path.match(/^\/api\/clips\/(\d+)\/thumb$/);
  if (thumb && m === "GET") {
    const r = await env.DB.prepare("SELECT thumb, thumb_type FROM clips WHERE id=?").bind(Number(thumb[1])).first();
    if (!r || !r.thumb) return err(404, "No thumbnail");
    return new Response(new Uint8Array(r.thumb), { headers: { "Content-Type": r.thumb_type || "image/png", "Cache-Control": "private, max-age=86400" } });
  }
  if (path === "/api/commands" && m === "GET") {
    return json({ commands: (await env.DB.prepare(`SELECT ${CMD_COLS} FROM commands ORDER BY created DESC LIMIT 20`).all()).results, labels: COMMANDS });
  }
  const oneCmd = path.match(/^\/api\/commands\/(\d+)$/);
  if (oneCmd && m === "GET") {
    const r = await env.DB.prepare("SELECT * FROM commands WHERE id=?").bind(Number(oneCmd[1])).first();
    return r ? json({ command: r, label: COMMANDS[r.type] || r.type }) : err(404, "Not found");
  }
  if (path === "/api/settings/pi" && m === "GET") return json({ settings: await piSettings(env) });
  if (path === "/api/settings/pi" && m === "POST") {
    const b = await readJson(req);
    const cur = await piSettings(env);
    let changed = false;
    for (const [k, v] of Object.entries(b || {})) {
      const c = cleanSetting(k, v);
      if (c !== undefined && cur[k] !== c) { cur[k] = c; changed = true; }
    }
    if (changed) { cur.rev = (cur.rev || 0) + 1; await kvSet(env, "pi_settings", JSON.stringify(cur)); }
    return json({ ok: true, settings: cur, plan: await planUsage(env, cur) });
  }
  if (path === "/api/settings/wifi" && m === "GET") {
    let w = null;
    try { w = JSON.parse((await kvGet(env, "wifi")) || "null"); } catch { w = null; }
    return json({ wifi: w });
  }
  if (path === "/api/settings/wifi" && m === "POST") {
    const b = await readJson(req);
    const ssid = String(b.ssid || "").slice(0, 64), password = String(b.password || "").slice(0, 64);
    if (!ssid) { await env.DB.prepare("DELETE FROM kv WHERE k='wifi'").run(); return json({ ok: true, wifi: null }); }
    await kvSet(env, "wifi", JSON.stringify({ ssid, password }));
    return json({ ok: true, wifi: { ssid, password } });
  }
  if (path === "/api/settings/shortcut-key" && m === "POST") {
    const b = await readJson(req);
    if (b.remove) { await env.DB.prepare("DELETE FROM kv WHERE k='shortcut_key_hash'").run(); return json({ ok: true, key: null }); }
    const key = randomToken(18);
    await kvSet(env, "shortcut_key_hash", await sha256hex(key));
    return json({ ok: true, key, base: `${url.protocol}//${url.host}/api/x/${key}` });
  }
  if (path === "/api/skymap" && m === "GET") {
    let sky = null;
    try { sky = JSON.parse((await kvGet(env, "skymap")) || "null"); } catch { sky = null; }
    return json({ sky });
  }
  if (path === "/api/speedtests" && m === "GET") {
    const days = Math.min(Number(url.searchParams.get("days")) || 30, 365);
    const rows = (await env.DB.prepare("SELECT * FROM speedtests WHERE at > ? ORDER BY at DESC LIMIT 200").bind(now() - days * 86400).all()).results;
    return json({ rows });
  }
  if (path === "/api/outages" && m === "GET") {
    const days = Math.min(Number(url.searchParams.get("days")) || 7, 90);
    const rows = (await env.DB.prepare("SELECT start, end, cause FROM outages WHERE start > ? ORDER BY start DESC LIMIT 300").bind(now() - days * 86400).all()).results;
    const perDay = (await env.DB.prepare("SELECT day, awake_s, starlink_s, good_s, energy_wh FROM usage_daily WHERE day >= ? ORDER BY day").bind(dayOf(now() - (days - 1) * 86400)).all()).results;
    return json({ days, rows, per_day: perDay });
  }
  if (path === "/api/timeline" && m === "GET") {
    const days = Math.min(Number(url.searchParams.get("days")) || 7, 60);
    const since = now() - days * 86400;
    const [alerts, outs, drives, tests] = await Promise.all([
      env.DB.prepare("SELECT at, title, message, category, link FROM alerts WHERE at > ? ORDER BY at DESC LIMIT 300").bind(since).all(),
      env.DB.prepare("SELECT start, end, cause FROM outages WHERE start > ? ORDER BY start DESC LIMIT 200").bind(since).all(),
      env.DB.prepare("SELECT start, end, checkins, net FROM drives WHERE start > ? ORDER BY start DESC LIMIT 200").bind(since).all(),
      env.DB.prepare("SELECT at, down, up, ping, auto FROM speedtests WHERE at > ? ORDER BY at DESC LIMIT 100").bind(since).all(),
    ]);
    return json({ days, alerts: alerts.results, outages: outs.results, sessions: drives.results, speedtests: tests.results });
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
      .bind(b.endpoint, b.keys.p256dh, b.keys.auth, String(b.label || "Phone").slice(0, 40), now(), JSON.stringify(PUSH_DEFAULTS)).run();
    return json({ ok: true });
  }
  if (path === "/api/push/unsubscribe" && m === "POST") {
    const b = await readJson(req);
    await env.DB.prepare("DELETE FROM push_subs WHERE endpoint=?").bind(String(b.endpoint || "")).run();
    return json({ ok: true });
  }
  if (path === "/api/push/prefs" && m === "POST") {
    const b = await readJson(req);
    const prefs = {};
    for (const k of Object.keys(PUSH_DEFAULTS)) prefs[k] = b.prefs?.[k] === undefined ? PUSH_DEFAULTS[k] : !!b.prefs[k];
    const q = b.prefs?.quiet;
    prefs.quiet = { on: !!(q && q.on), from: Math.max(0, Math.min(23, Number(q?.from ?? 22))), to: Math.max(0, Math.min(23, Number(q?.to ?? 7))) };
    await env.DB.prepare("UPDATE push_subs SET prefs=? WHERE endpoint=?").bind(JSON.stringify(prefs), String(b.endpoint || "")).run();
    return json({ ok: true, prefs });
  }
  if (path === "/api/push/status" && m === "POST") {
    const b = await readJson(req);
    const r = await env.DB.prepare("SELECT label, prefs, last_ok FROM push_subs WHERE endpoint=?").bind(String(b.endpoint || "")).first();
    const n = await env.DB.prepare("SELECT COUNT(*) AS n FROM push_subs").first();
    return json({ subscribed: !!r, prefs: r ? { ...PUSH_DEFAULTS, ...JSON.parse(r.prefs || "{}") } : null, devices: n.n });
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
    const prevAt = Number(await kvGet(env, "latest_at")) || 0;
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
    // Time awake / on Starlink / with a good signal, added up per day.
    const dt = prevAt && t - prevAt < 120 ? Math.min(t - prevAt, 60) : 0;
    const onSl = s.pi?.network === "starlink";
    const u = s.starlink?.usage_today_mb || {};
    await env.DB.prepare(`INSERT INTO usage_daily(day, down_mb, up_mb, clips_mb, energy_wh, awake_s, starlink_s, good_s) VALUES(?,?,?,?,?,?,?,?)
      ON CONFLICT(day) DO UPDATE SET down_mb=MAX(COALESCE(down_mb,0), excluded.down_mb), up_mb=MAX(COALESCE(up_mb,0), excluded.up_mb),
      clips_mb=MAX(COALESCE(clips_mb,0), excluded.clips_mb), energy_wh=MAX(COALESCE(energy_wh,0), excluded.energy_wh),
      awake_s=COALESCE(awake_s,0)+excluded.awake_s, starlink_s=COALESCE(starlink_s,0)+excluded.starlink_s, good_s=COALESCE(good_s,0)+excluded.good_s`)
      .bind(dayOf(t), num(u.down) || 0, num(u.up) || 0, num(s.teslacam?.starlink_uploaded_today_mb) || 0, num(s.starlink?.energy_today_wh) || 0,
        dt, onSl ? dt : 0, onSl && s.starlink?.quality === "good" ? dt : 0).run();

    // "Car awake" sessions: a gap of 10+ minutes between check-ins starts a new one.
    let sess = null;
    try { sess = JSON.parse((await kvGet(env, "sess")) || "null"); } catch { sess = null; }
    if (!sess || t - sess.last > 600) {
      if (sess && sess.last - sess.start >= 60) {
        await env.DB.prepare("INSERT OR REPLACE INTO drives(start, end, checkins, net) VALUES(?,?,?,?)").bind(sess.start, sess.last, sess.n || 0, sess.net || null).run();
      }
      const gap = sess ? t - sess.last : null;
      sess = { start: t, last: t, n: 1, net: s.pi?.network || null, announced: false };
      const hr = denverClock(t).h;
      if (gap !== null && gap > 1800 && hr >= 0 && hr < 5) {
        await addAlert(env, ctx, { title: `Car woke up at ${clockText(t)}`, category: "wake", link: "/#activity",
          message: "The Pi just turned on, so the car is awake. Usually that's Sentry, charging or the Tesla app. Worth a look if you weren't expecting it." });
      }
    } else {
      sess.last = t; sess.n = (sess.n || 0) + 1;
      if (onSl) sess.net = "starlink";
    }
    if (!sess.announced && onSl && s.starlink?.state === "CONNECTED" && s.pi?.internet) {
      sess.announced = true;
      if (t - sess.start < 900) {
        const p = notifyAll(env, { title: "Starlink is online in the car", body: `Connected · ${Math.round(s.starlink.ping_ms || 0)} ms`, url: "/#starlink", tag: "online" }, "online", ctx);
        if (!ctx) await p;
      }
    }
    await kvSet(env, "sess", JSON.stringify(sess));

    const st = await piSettings(env);
    const plan = await planUsage(env, st);
    if (plan) {
      const mark = plan.pct >= 100 ? 100 : plan.pct >= 80 ? 80 : 0;
      const tag = `${plan.cycle_start}:${mark}`;
      if (mark && (await kvGet(env, "plan_alerted")) !== tag) {
        await kvSet(env, "plan_alerted", tag);
        await addAlert(env, ctx, { title: mark === 100 ? "Starlink data plan used up" : "Starlink data plan at 80%", category: "problem", link: "/#starlink",
          message: `${plan.used_gb} of ${plan.gb} GB used since ${plan.cycle_start}.${st.plan_protect ? " Footage uploads over Starlink pause at 90% and wait for home WiFi." : ""}` });
      }
    }
    const pending = await env.DB.prepare("SELECT COUNT(*) AS n FROM commands WHERE status='queued'").first();
    const lv = await latestVersion(env, ctx);
    const send = { ...st, plan_pct: plan ? plan.pct : null };
    delete send.plan_gb; delete send.plan_reset_day;
    return json({ ok: true, commands_waiting: pending.n, latest_version: lv.version, settings: send });
  }
  if (path === "/api/pi/history" && m === "POST") {
    // Readings the Pi kept while it couldn't reach us (one a minute).
    const b = await readJson(req);
    const rows = (b.rows || []).slice(0, 300).filter((r) => num(r.ts) !== null && r.ts > now() - 4 * 86400 && r.ts < now() + 60);
    const stmts = rows.map((r) => env.DB.prepare(`INSERT OR IGNORE INTO history(ts, net, internet, dish_ok, state, quality, ping, drop_pct, obstructed, down, up, power, temp, load1, wifi_signal, gadget, usb_link, lat, lon)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).bind(num(r.ts), r.net || null, r.internet ? 1 : 0, r.dish_ok ? 1 : 0, r.state || null, r.quality || null,
      num(r.ping), num(r.drop_pct), num(r.obstructed), num(r.down), num(r.up), num(r.power), num(r.temp), num(r.load1), num(r.wifi_signal),
      r.gadget || null, r.usb_link || null, num(r.lat), num(r.lon)));
    const perDay = {};
    for (const r of rows) {
      const d = (perDay[dayOf(r.ts)] ||= { a: 0, s: 0, g: 0 });
      d.a += 60; if (r.net === "starlink") { d.s += 60; if (r.quality === "good") d.g += 60; }
    }
    for (const [day, d] of Object.entries(perDay)) {
      stmts.push(env.DB.prepare(`INSERT INTO usage_daily(day, awake_s, starlink_s, good_s) VALUES(?,?,?,?) ON CONFLICT(day) DO UPDATE SET
        awake_s=COALESCE(awake_s,0)+excluded.awake_s, starlink_s=COALESCE(starlink_s,0)+excluded.starlink_s, good_s=COALESCE(good_s,0)+excluded.good_s`).bind(day, d.a, d.s, d.g));
    }
    for (let i = 0; i < stmts.length; i += 50) await env.DB.batch(stmts.slice(i, i + 50));
    return json({ ok: true, saved: rows.length });
  }
  if (path === "/api/pi/outages" && m === "POST") {
    const b = await readJson(req);
    const stmts = (b.outages || []).slice(0, 300).filter((o) => num(o[0]) !== null && num(o[1]) !== null && o[1] >= o[0]).map((o) =>
      env.DB.prepare("INSERT OR REPLACE INTO outages(start, end, cause) VALUES(?,?,?)").bind(num(o[0]), num(o[1]), String(o[2] || "no service").slice(0, 60)));
    for (let i = 0; i < stmts.length; i += 50) await env.DB.batch(stmts.slice(i, i + 50));
    return json({ ok: true, saved: stmts.length });
  }
  if (path === "/api/pi/speedtest" && m === "POST") {
    const r = await readJson(req);
    if (num(r.down_mbps) === null) return err(400, "No result");
    const at = num(r.at) && r.at < now() + 60 && r.at > now() - 86400 ? r.at : now();
    await env.DB.prepare("INSERT OR REPLACE INTO speedtests(at, down, up, ping, jitter, network, profile, auto, used_mb, server) VALUES(?,?,?,?,?,?,?,?,?,?)")
      .bind(at, num(r.down_mbps), num(r.up_mbps), num(r.ping_ms), num(r.jitter_ms), r.network || null, r.profile || null, r.auto ? 1 : 0, num(r.used_mb), r.server ? String(r.server).slice(0, 8) : null).run();
    return json({ ok: true });
  }
  if (path === "/api/pi/skymap" && m === "POST") {
    const b = await readJson(req);
    if (!b.data || String(b.data).length > 60000 || !num(b.w) || !num(b.h)) return err(400, "Bad sky map");
    await kvSet(env, "skymap", JSON.stringify({ w: b.w, h: b.h, known: num(b.known), at: now(), data: String(b.data) }));
    return json({ ok: true });
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
    let files = null;
    if (Array.isArray(c.files)) {
      const f = JSON.stringify(c.files.slice(0, 80).map((x) => [String(x[0]).slice(0, 19), String(x[1]).slice(0, 20), String(x[2]).slice(0, 60)]));
      if (f.length < 12000) files = f;
    }
    await env.DB.prepare(`INSERT INTO clips(kind, folder, drive_id, drive_url, size_mb, reason, city, lat, lon, event_ts, uploaded_at, network, thumb, thumb_type, files, camera, encrypted)
      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(kind, folder) DO UPDATE SET drive_id=excluded.drive_id, drive_url=excluded.drive_url,
      size_mb=excluded.size_mb, uploaded_at=excluded.uploaded_at, thumb=COALESCE(excluded.thumb, clips.thumb), files=COALESCE(excluded.files, clips.files), encrypted=excluded.encrypted`).bind(
      kind, String(c.folder).slice(0, 80), c.drive_id || null, driveUrl, num(c.size_mb), c.reason || null, c.city || null,
      num(c.lat), num(c.lon), c.event_ts || null, now(), c.network || null, thumb, c.thumb_type || "image/png", files,
      c.camera === undefined || c.camera === null ? null : String(c.camera).slice(0, 4), c.encrypted ? 1 : 0).run();
    const label = kind === "sentry" ? "Sentry event saved" : kind === "requested" ? "Your dashcam request is ready" : "Dashcam clip saved";
    const where = c.city ? ` in ${c.city}` : "";
    await addAlert(env, ctx, { title: label, message: `${c.folder}${where} is in Google Drive.`, category: "clip", link: "/#footage" });
    return json({ ok: true });
  }
  if (path === "/api/pi/alert" && m === "POST") {
    const a = await readJson(req);
    await addAlert(env, ctx, { title: a.title || "Car Atlas", message: a.message || "", category: ["clip", "problem", "info"].includes(a.category) ? a.category : "info", link: a.link || "/#home", at: num(a.at) });
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
    const output = b.output ? String(b.output).slice(-16000) : null;
    await env.DB.prepare("UPDATE commands SET status=?, done=?, result=?, output=COALESCE(?, output) WHERE id=?")
      .bind(b.ok ? "done" : "failed", now(), String(b.result || "").slice(0, 500), output, Number(done[1])).run();
    return json({ ok: true });
  }
  return err(404, "Not found");
}

// ---------- Siri Shortcuts (a private link with its own key, no login) ----------
const text = (body, status = 200) => new Response(body, { status, headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" } });
async function queueCommand(env, type, args = {}) {
  const open = await env.DB.prepare("SELECT id FROM commands WHERE type=? AND status IN ('queued','picked')").bind(type).first();
  if (open) return false;
  await env.DB.prepare("INSERT INTO commands(type,args,status,created) VALUES(?,?,'queued',?)").bind(type, JSON.stringify(args), now()).run();
  return true;
}
async function spokenStatus(env) {
  const latest = await kvGet(env, "latest");
  const at = Number(await kvGet(env, "latest_at")) || 0;
  if (!latest) return "Car Atlas hasn't heard from the Pi yet.";
  const s = JSON.parse(latest), t = now();
  const clips = await env.DB.prepare("SELECT COUNT(*) AS n FROM clips WHERE uploaded_at >= ?").bind(denverMidnight(t)).first();
  const clipTxt = clips.n ? ` ${clips.n} clip${clips.n === 1 ? "" : "s"} saved today.` : "";
  if (t - at > 150) return `The car is asleep. The Pi last checked in ${durText(t - at)} ago.${clipTxt}`;
  const d = s.starlink || {}, cam = s.teslacam || {}, pi = s.pi || {};
  const sl = pi.network === "starlink"
    ? (d.state === "CONNECTED" ? `Starlink is connected at ${Math.round(d.ping_ms || 0)} milliseconds${d.quality === "weak" ? ", but the signal is weak" : ""}.` : "Starlink is looking for satellites.")
    : `The Pi is on ${pi.network === "home" ? "home WiFi" : pi.wifi_ssid || "no WiFi"}.`;
  const dash = cam.usb_link === "configured" ? "The dashcam is recording to the Pi." : "The car is not connected to the dashcam drive.";
  return `The car is awake. ${sl} ${dash} ${pi.cpu_temp_c ? `The Pi is at ${Math.round(pi.cpu_temp_c)} degrees.` : ""}${clipTxt}`;
}
async function handleShortcut(req, env, ctx, url, path) {
  const m = path.match(/^\/api\/x\/([A-Za-z0-9_-]{10,60})\/([a-z-]+)$/);
  const stored = await kvGet(env, "shortcut_key_hash");
  if (!m || !stored || !safeEqual(await sha256hex(m[1]), stored)) return text("That link isn't valid anymore. Make a new one in Car Atlas, Settings, Siri Shortcuts.", 403);
  const action = m[2];
  if (action === "status") return text(await spokenStatus(env));
  if (action === "save") {
    const minutes = Math.max(1, Math.min(60, Number(url.searchParams.get("minutes")) || 10));
    const ok = await queueCommand(env, "upload_recent", { minutes });
    return text(ok ? `Okay. Saving the last ${minutes} minutes of dashcam to Google Drive.` : "A dashcam save is already on its way.");
  }
  if (action === "speedtest") {
    const ok = await queueCommand(env, "speedtest");
    return text(ok ? "Okay. Running a speed test on the Starlink. The result shows up in Car Atlas in about half a minute." : "A speed test is already running.");
  }
  return text("Car Atlas doesn't know that one. Try status, save, or speedtest.", 404);
}

// ---------- once-an-hour jobs ----------
async function dailyRecap(env, ctx) {
  const t = now(), day = dayOf(t);
  if (denverClock(t).h !== 20 || (await kvGet(env, "recap_day")) === day) return;
  await kvSet(env, "recap_day", day);
  const u = await env.DB.prepare("SELECT * FROM usage_daily WHERE day=?").bind(day).first();
  if (!u || (u.awake_s || 0) < 300) return;      // car barely on today: nothing worth a ping
  const mid = denverMidnight(t);
  const clips = await env.DB.prepare("SELECT COUNT(*) AS n FROM clips WHERE uploaded_at >= ?").bind(mid).first();
  const drops = await env.DB.prepare("SELECT COUNT(*) AS n FROM outages WHERE start >= ?").bind(mid).first();
  const parts = [`Awake ${durText(u.awake_s)}`];
  if ((u.starlink_s || 0) > 120) parts.push(`Starlink good ${Math.round((100 * (u.good_s || 0)) / u.starlink_s)}% of the time`);
  const gb = ((u.down_mb || 0) + (u.up_mb || 0)) / 1000;
  if (gb >= 0.05) parts.push(`${gb.toFixed(1)} GB used`);
  if (drops.n) parts.push(`${drops.n} drop${drops.n === 1 ? "" : "s"}`);
  parts.push(`${clips.n} clip${clips.n === 1 ? "" : "s"} saved`);
  await addAlert(env, ctx, { title: "Today in the Model Y", message: parts.join(" · ") + ".", category: "recap", link: "/#activity" });
}
async function silentCheck(env, ctx) {
  const at = Number(await kvGet(env, "latest_at")) || 0;
  if (!at || now() - at < 4 * 86400 || (await kvGet(env, "silent_alerted")) === String(at)) return;
  await kvSet(env, "silent_alerted", String(at));
  await addAlert(env, ctx, { title: "Haven't heard from the Pi in 4 days", category: "problem",
    message: "If the car has been driven since then, the Pi may be unplugged or stuck. Check the cable in the glovebox." });
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
      if (path.startsWith("/api/x/")) return await handleShortcut(req, env, ctx, url, path);
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

  async scheduled(event, env, ctx) {
    const t = now();
    try { await dailyRecap(env, ctx); } catch (e) { console.log("recap failed", String(e)); }
    try { await silentCheck(env, ctx); } catch (e) { console.log("silent check failed", String(e)); }
    if (new Date(t * 1000).getUTCHours() % 6 !== 0) return;
    const st = await piSettings(env);
    const jobs = [
      env.DB.prepare("DELETE FROM history WHERE ts < ?").bind(t - 120 * 86400),
      env.DB.prepare("DELETE FROM login_attempts WHERE ts < ?").bind(t - 86400),
      env.DB.prepare("DELETE FROM sessions WHERE expires < ?").bind(t),
      env.DB.prepare("DELETE FROM pairing WHERE expires < ?").bind(t - 86400),
      env.DB.prepare("DELETE FROM commands WHERE created < ?").bind(t - 30 * 86400),
      env.DB.prepare("UPDATE commands SET output=NULL WHERE created < ? AND output IS NOT NULL").bind(t - 7 * 86400),
      env.DB.prepare("DELETE FROM alerts WHERE id NOT IN (SELECT id FROM alerts ORDER BY at DESC LIMIT 500)"),
      env.DB.prepare("UPDATE commands SET status='expired' WHERE status='queued' AND created < ?").bind(t - 86400),
      env.DB.prepare("DELETE FROM outages WHERE start < ?").bind(t - 180 * 86400),
      env.DB.prepare("DELETE FROM drives WHERE start < ?").bind(t - 180 * 86400),
      env.DB.prepare("DELETE FROM speedtests WHERE at < ?").bind(t - 365 * 86400),
    ];
    // If "keep footage for N days" is on, the Pi clears old footage from Drive; drop the matching entries here too.
    if (st.retention_days) jobs.push(env.DB.prepare("DELETE FROM clips WHERE uploaded_at < ?").bind(t - st.retention_days * 86400));
    await env.DB.batch(jobs);
  },
};
