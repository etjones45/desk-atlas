/* Car Atlas phone app */
(() => {
  "use strict";
  const $app = document.getElementById("app");
  const DRIVE = {
    root: "https://drive.google.com/drive/folders/1MDtz0MdP8wSYrJMTbo-mmmNTcK0JkzLw",
    dashcam: "https://drive.google.com/drive/folders/1B8RdEvhfc_Bk35iA9ON2iNTZHDmFbHmG",
    sentry: "https://drive.google.com/drive/folders/1JfANie1Q0J9mF424Ezawx67P5unRmEnX",
  };
  const INSTALL_URL = "https://raw.githubusercontent.com/etjones45/desk-atlas/car/car/install.sh";
  const APP_VERSION = "1.2"; // this app build; the server reports its own (they match after a deploy)

  // ---------- icons ----------
  const P = {
    home: '<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    film: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9l5 3-5 3z"/>',
    sat: '<path d="M5 19a9 9 0 0 1 0-12.7"/><path d="M8.5 15.5a4 4 0 0 1 0-5.6"/><circle cx="12" cy="12.7" r="1.6"/><path d="M13.5 11.2L19 5.7"/><path d="M16 4h4v4"/>',
    map: '<path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',
    cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
    refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
    car: '<path d="M5 16l1.5-5.5A2 2 0 0 1 8.4 9h7.2a2 2 0 0 1 1.9 1.5L19 16"/><rect x="3" y="15" width="18" height="4" rx="1.5"/><circle cx="7.5" cy="19.5" r="1.3"/><circle cx="16.5" cy="19.5" r="1.3"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    cloud: '<path d="M7 18a4.5 4.5 0 0 1-.6-9 6 6 0 0 1 11.4 1.6A3.8 3.8 0 0 1 17.5 18z"/>',
    therm: '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/><path d="M12 9v7"/>',
    data: '<path d="M4 7c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3z"/><path d="M4 7v10c0 1.7 3.6 3 8 3s8-1.3 8-3V7"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    rec: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4" fill="currentColor"/>',
    save: '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 19h16"/>',
    pin: '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    power: '<path d="M12 3v8"/><path d="M6.3 6.3a8 8 0 1 0 11.4 0"/>',
    bell: '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    alert: '<path d="M12 3l9.5 17H2.5z"/><path d="M12 10v4M12 17.5v.5"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    upload: '<path d="M12 16V4"/><path d="M7 9l5-5 5 5"/><path d="M4 20h16"/>',
    drive: '<path d="M8 3h8l6 10-4 7H6l-4-7z"/><path d="M8 3l6 10h8M2 13h12l-4 7"/>',
    wifi: '<path d="M2 8.5a15 15 0 0 1 20 0"/><path d="M5.5 12a10 10 0 0 1 13 0"/><path d="M9 15.5a5 5 0 0 1 6 0"/><circle cx="12" cy="19" r="1"/>',
    bolt: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    out: '<path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4"/><path d="M10 16l-4-4 4-4"/><path d="M6 12h10"/>',
    usb: '<path d="M12 21V5"/><path d="M9 6l3-3 3 3"/><path d="M12 15l-4-3V9"/><path d="M12 13l4-3V8"/><circle cx="8" cy="8" r="1.4"/><rect x="14.6" y="6" width="2.8" height="2.6"/><circle cx="12" cy="20" r="1.6"/>',
    tag: '<path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z"/><circle cx="8" cy="8" r="1.5"/>',
    star: '<path d="M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z"/>',
    gauge: '<path d="M4 17a8 8 0 1 1 16 0"/><path d="M12 17l4.5-5.5"/><circle cx="12" cy="17" r="1.2"/>',
    qr: '<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><path d="M14 14h2v2h-2zM18 14h2M14 18h2v2M18 18h2v2"/>',
    wheel: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.2"/><path d="M12 14.2V21M9.9 11.3L3.6 9.2M14.1 11.3l6.3-2.1"/>',
    pulse: '<path d="M3 12h4l2.5-6 4 12 2.5-6h5"/>',
    pause: '<rect x="6" y="5" width="4" height="14" rx="1"/><rect x="14" y="5" width="4" height="14" rx="1"/>',
    play: '<path d="M7 5l12 7-12 7z"/>',
    list: '<path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
    moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
    mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    x: '<path d="M6 6l12 12M18 6L6 18"/>',
    users: '<circle cx="9" cy="8" r="3.2"/><path d="M3 20a6 6 0 0 1 12 0"/><circle cx="17.5" cy="9" r="2.4"/><path d="M16 14.2a5 5 0 0 1 5 5"/>',
    gps: '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
    speed: '<path d="M4 18a8 8 0 1 1 16 0"/><path d="M12 18l4-6"/>',
    ext: '<path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  };
  const ic = (n, extra = "") => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra}>${P[n] || ""}</svg>`;

  // ---------- utils ----------
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const nowS = () => Date.now() / 1000;
  const fmtN = (v, nd = 0, unit = "") => (v === null || v === undefined || isNaN(v) ? "—" : Number(v).toFixed(nd) + unit);
  function ago(ts) {
    if (!ts) return "never";
    const s = Math.max(0, nowS() - ts);
    if (s < 45) return "just now";
    if (s < 90) return "1 min ago";
    if (s < 3600) return Math.round(s / 60) + " min ago";
    if (s < 86400) return Math.round(s / 3600) + " h ago";
    if (s < 86400 * 14) return Math.round(s / 86400) + " days ago";
    return new Date(ts * 1000).toLocaleDateString([], { month: "short", day: "numeric" });
  }
  function dur(sec) {
    if (sec === null || sec === undefined) return "—";
    const d = Math.floor(sec / 86400), h = Math.floor((sec % 86400) / 3600), m = Math.floor((sec % 3600) / 60);
    return d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : `${m}m`;
  }
  function durShort(sec) {
    sec = Math.max(0, Math.round(sec || 0));
    const h = Math.floor(sec / 3600), m = Math.round((sec % 3600) / 60);
    return h ? `${h}h ${m}m` : m ? `${m} min` : `${sec} s`;
  }
  const BATTERY_KWH = 75; // rough Model Y pack size, for "about X% of the battery"
  const gbText = (mb) => (mb >= 1000 ? (mb / 1000).toFixed(1) + " GB" : Math.round(mb || 0) + " MB");
  // Settings the Pi follows (uploads, speed tests, ...). Saved in the app; the Pi picks them up at its next check-in.
  const S = () => (state.ov && state.ov.settings) || {};
  async function saveSetting(patch, msg) {
    try {
      const r = await api("/api/settings/pi", { method: "POST", body: patch });
      if (state.ov) { state.ov.settings = r.settings; state.ov.plan = r.plan; state.ov.settings_applied = false; }
      const awake = derive().fresh;
      toast(msg || (awake ? "Saved. The Pi picks it up within a minute." : "Saved. The Pi picks it up next time the car is awake."));
      render();
    } catch (e) { if (e.message !== "auth") toast(e.message); }
  }
  const toggleRow = (key, title, desc, on) => `<label class="toggle"><span><div style="font-weight:600">${title}</div><div class="muted small">${desc}</div></span>
    <span class="switch"><input type="checkbox" data-set="${key}" ${on ? "checked" : ""}><span></span></span></label>`;
  function bindSettings(root) {
    root.querySelectorAll("input[data-set]").forEach((i) => i.onchange = () => saveSetting({ [i.dataset.set]: i.dataset.invert ? !i.checked : i.checked }));
    root.querySelectorAll("button[data-setk]").forEach((b) => b.onclick = () => {
      const v = isNaN(Number(b.dataset.setv)) ? b.dataset.setv : Number(b.dataset.setv);
      if (b.dataset.confirm && !b.classList.contains("on")) {
        confirmSheet({ title: b.dataset.ctitle || "Change this?", body: esc(b.dataset.confirm), yes: "Yes, change it", danger: true }).then((y) => y && saveSetting({ [b.dataset.setk]: v }));
      } else saveSetting({ [b.dataset.setk]: v });
    });
  }
  const chipSet = (key, options, cur, extra = "") => `<div class="chips">${options.map(([v, l]) => `<button class="chip ${String(cur) === String(v) ? "on" : ""}" data-setk="${key}" data-setv="${v}" ${v && extra ? extra : ""}>${l}</button>`).join("")}</div>`;

  function friendlyDate(d) {
    if (!d || isNaN(d)) return "";
    const today = new Date(); const y = new Date(); y.setDate(today.getDate() - 1);
    const t = d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    if (d.toDateString() === today.toDateString()) return `Today ${t}`;
    if (d.toDateString() === y.toDateString()) return `Yesterday ${t}`;
    if ((today - d) / 864e5 < 6) return `${d.toLocaleDateString([], { weekday: "short" })} ${t}`;
    return `${d.toLocaleDateString([], { month: "short", day: "numeric" })} ${t}`;
  }
  function folderDate(folder) {
    const m = String(folder || "").match(/(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})/);
    return m ? new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]) : null;
  }
  function reasonText(c) {
    const r = String(c.reason || "").toLowerCase();
    if (c.kind === "requested") return "You asked for this";
    if (r.includes("honk")) return "You honked";
    if (r.includes("object_detection")) return "Someone came close";
    if (r.includes("accel")) return "Car was bumped";
    if (r.includes("panic") || r.includes("alarm")) return "Alarm went off";
    if (r.includes("user_interaction") || r.includes("dashcam")) return "You saved this";
    return c.kind === "sentry" ? "Sentry event" : "Saved clip";
  }
  const kindLabel = { dashcam: "Dashcam", sentry: "Sentry", requested: "Requested" };
  function cmpVer(a, b) {
    if (!a || !b) return null;
    const pa = String(a).split(".").map((x) => parseInt(x, 10) || 0), pb = String(b).split(".").map((x) => parseInt(x, 10) || 0);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) { const d = (pa[i] || 0) - (pb[i] || 0); if (d) return d > 0 ? 1 : -1; }
    return 0;
  }
  // Versions: what the Pi runs vs. the newest release on GitHub (what it should be on).
  function verInfo() {
    const ov = state.ov || {};
    const V = ov.versions || {};
    const pi = V.pi, latest = V.latest;
    const c = cmpVer(pi, latest);
    const fresh = !!(ov.status_at && ov.server_time - ov.status_at < 150);
    let level = "", text = "Waiting for the Pi", short = "—";
    if (pi && latest) {
      if (c === 0) { level = "ok"; text = "Up to date"; short = `v${pi}`; }
      else if (c < 0) { level = "warn"; text = `Update waiting: v${pi} → v${latest}`; short = `v${pi} → v${latest}`; }
      else { level = "accent"; text = `Ahead of release (v${pi})`; short = `v${pi}`; }
    } else if (pi) { text = `Running v${pi}`; short = `v${pi}`; }
    const up = V.pi_update || {};
    let note = "";
    if (c !== null && c < 0) {
      note = fresh ? "The Pi is online, so it should pick this up within a few minutes. Tap Update now to start it right away."
        : "The Pi updates itself the next time the car is awake and online. It checks right after it turns on.";
    }
    return { ...V, level, text, short, behind: c !== null && c < 0, note, upd: up, fresh };
  }
  const verBadge = (v, cls = "") => v ? `<span class="ver ${cls}">v${esc(v)}</span>` : `<span class="ver">—</span>`;
  function greet() {
    const h = new Date().getHours();
    return (h < 5 ? "Up late" : h < 12 ? "Morning" : h < 17 ? "Afternoon" : "Evening") + ", ET";
  }
  const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const isDark = () => matchMedia("(prefers-color-scheme: dark)").matches;
  const standalone = () => matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
  const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent);

  function toast(msg, ms = 3200) {
    document.querySelectorAll(".toast").forEach((t) => t.remove());
    const t = document.createElement("div");
    t.className = "toast"; t.textContent = msg; t.setAttribute("role", "status");
    document.body.append(t);
    setTimeout(() => t.remove(), ms);
  }
  function sheet(html, onMount) {
    const scrim = document.createElement("div");
    scrim.className = "scrim";
    scrim.innerHTML = `<div class="sheet" role="dialog" aria-modal="true"><div class="grab"></div>${html}</div>`;
    const close = () => scrim.remove();
    scrim.addEventListener("click", (e) => { if (e.target === scrim) close(); });
    document.body.append(scrim);
    onMount && onMount(scrim.querySelector(".sheet"), close);
    return close;
  }
  function confirmSheet({ title, body, yes, danger }) {
    return new Promise((resolve) => {
      sheet(`<h2>${esc(title)}</h2><div class="muted">${body}</div>
        <div class="row"><button class="btn ghost" data-no style="flex:1">Cancel</button>
        <button class="btn ${danger ? "danger" : "primary"}" data-yes style="flex:1">${esc(yes)}</button></div>`, (el, close) => {
        el.querySelector("[data-no]").onclick = () => { close(); resolve(false); };
        el.querySelector("[data-yes]").onclick = () => { close(); resolve(true); };
      });
    });
  }
  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); toast("Copied"); }
    catch { toast("Couldn't copy. Press and hold to select it."); }
  }

  // ---------- API ----------
  async function api(path, opts = {}) {
    const res = await fetch(path, {
      method: opts.method || "GET",
      headers: opts.body ? { "Content-Type": "application/json" } : {},
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      credentials: "same-origin",
    });
    if (res.status === 401) { state.authed = false; renderLogin(); throw new Error("auth"); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
    return data;
  }

  // ---------- state ----------
  const state = { authed: null, me: null, ov: null, route: "home", charts: [], map: null, footKind: "all", clips: null, clipsDone: false, stRange: 24, mapDays: 30, mapProblems: false, loading: false };

  function derive() {
    const ov = state.ov || {};
    const s = ov.status;
    const fresh = !!(s && ov.status_at && ov.server_time - ov.status_at < 150);
    const pi = (s && s.pi) || {}, d = (s && s.starlink) || {}, link = (s && s.link) || {}, cam = (s && s.teslacam) || {};
    const onStarlink = pi.network === "starlink";
    let level = "idle", headline = "Waiting for the Pi", note = "";
    if (!ov.paired) { level = "idle"; headline = "Let's connect your Pi"; note = "Finish setup below and live status shows up here."; }
    else if (!s) { level = "idle"; headline = "Pi is connected"; note = "Waiting for its first check-in. Wake the car so the Pi turns on."; }
    else if (!fresh) { level = "idle"; headline = "Car is asleep"; note = `Last check-in ${ago(ov.status_at)}. The Pi is off while the car sleeps. With Sentry Mode on, the car stays awake and so does the Pi.`; }
    else if (cam.gadget === "unsupported" || cam.gadget === "error") { level = "bad"; headline = "Dashcam isn't recording to the Pi"; note = "Keep a USB flash drive in the car until this is fixed."; }
    else if (cam.gadget === "attached" && cam.usb_link !== "configured" && (pi.uptime_s || 0) > 120) { level = "bad"; headline = "Car isn't seeing the dashcam drive"; note = "The Pi is ready but the car hasn't connected. The car's cable must be in the Pi's USB0 port. Footage tab shows where."; }
    else if (onStarlink && !link.pi_talking_to_dish) { level = "bad"; headline = "Pi can't reach the Starlink"; note = "It's on the Starlink WiFi but the dish isn't answering."; }
    else if (!pi.internet) { level = "warn"; headline = "No internet right now"; note = "Clips and status wait until the connection comes back."; }
    else if (onStarlink && d.quality === "weak") { level = "warn"; headline = "Starlink is a little weak"; note = "Trees, bridges or buildings nearby. It should clear up."; }
    else if (onStarlink && d.quality === "down") { level = "warn"; headline = "Starlink is finding satellites"; note = "Usually takes a minute after the car wakes."; }
    else { level = "ok"; headline = cam.uploading ? "Uploading footage" : "Everything's working"; note = `Checked in ${ago(ov.status_at)} · on ${pi.wifi_ssid || "WiFi"}`; }
    const usb = cam.usb || {};
    const carOk = cam.usb_link === "configured";
    const outage = fresh && onStarlink ? d.outage : null;
    if (outage && level !== "bad") { level = "warn"; headline = "Starlink dropped out"; note = `No service for ${durShort(outage.seconds)} (${outage.cause}). It usually comes back on its own.`; }
    const motion = (s && s.motion) || null;
    return { s, fresh, pi, d, link, cam, usb, carOk, motion, onStarlink, level, headline, note, outage };
  }
  // Plain-language "what can I do on this connection right now"
  function worksNow(D) {
    if (!D.fresh) return [];
    const { pi, d } = D;
    if (!pi.internet) return [["No internet", "bad"]];
    if (!D.onStarlink) return [[pi.network === "home" ? "On home WiFi" : "On " + (pi.wifi_ssid || "WiFi"), "ok"]];
    if (D.outage || d.state !== "CONNECTED") return [["Calls: not right now", "bad"], ["Streaming: not right now", "bad"]];
    const ping = d.ping_ms || 999, drop = d.drop_pct || 0, blocked = d.currently_obstructed;
    const calls = blocked || drop > 4 || ping > 120 ? "bad" : drop > 1 || ping > 70 ? "warn" : "ok";
    const stream = blocked || drop > 8 ? "warn" : "ok";
    const word = { ok: "good", warn: "may be choppy", bad: "rough" };
    return [[`Video calls: ${word[calls]}`, calls], [`Streaming: ${stream === "ok" ? "good" : "may buffer"}`, stream], [`Browsing: good`, "ok"]];
  }
  function qualityBars(d, fresh) {
    if (!fresh || !d.reachable) return 0;
    if (d.state !== "CONNECTED") return 1;
    const ping = d.ping_ms || 999, drop = d.drop_pct || 0;
    if (d.currently_obstructed || drop > 5 || ping > 120) return 2;
    if (drop > 1 || ping > 60) return 3;
    return 4;
  }
  function barsHtml(q) {
    const col = q >= 4 ? "var(--ok)" : q === 3 ? "var(--ok)" : q === 2 ? "var(--warn)" : q === 1 ? "var(--bad)" : "var(--line)";
    return `<span class="bars" aria-label="Signal ${q} of 4">${[1, 2, 3, 4].map((i) => `<i style="background:${i <= q ? col : "var(--line)"}"></i>`).join("")}</span>`;
  }

  // ---------- shell ----------
  const TABS = [
    ["home", "Home", "home"], ["footage", "Footage", "film"], ["starlink", "Starlink", "sat"], ["map", "Map", "map"], ["pi", "Pi", "cpu"],
  ];
  const TITLES = { home: "Car Atlas", footage: "Footage", starlink: "Starlink", map: "Coverage map", pi: "Pi", settings: "Settings", activity: "Activity", drive: "Drive mode" };
  function renderShell() {
    $app.innerHTML = `
      <header class="topbar">
        <div class="title"><h1 id="ttl">Car Atlas</h1><div class="sub" id="tsub">2024 Model Y</div></div>
        <button class="icon-btn" id="btnRefresh" aria-label="Refresh">${ic("refresh")}</button>
        <a class="icon-btn" href="#settings" aria-label="Settings">${ic("gear")}</a>
      </header>
      <main id="view"></main>
      <nav class="tabbar" aria-label="Sections">
        ${TABS.map(([id, label, icon]) => `<a href="#${id}" data-tab="${id}">${ic(icon)}<span>${label}</span></a>`).join("")}
      </nav>`;
    document.getElementById("btnRefresh").onclick = () => refresh(true);
  }
  function setTitle() {
    document.getElementById("ttl").textContent = TITLES[state.route] || "Car Atlas";
    const { level, fresh } = derive();
    const V = verInfo();
    document.getElementById("tsub").textContent = (!state.ov ? "Loading…" : fresh ? (level === "ok" ? "All good" : level === "warn" ? "Heads up" : "Needs attention") + ` · ${ago(state.ov.status_at)}` : "Car asleep or offline") + (V.pi ? (V.behind ? " · Pi update waiting" : ` · v${V.pi}`) : "");
    document.querySelectorAll(".tabbar a").forEach((a) => a.classList.toggle("active", a.dataset.tab === state.route));
  }
  function destroyCharts() { state.charts.forEach((c) => c.destroy()); state.charts = []; }

  function render() {
    if (!state.authed) return renderLogin();
    if (!document.getElementById("view")) renderShell();
    destroyCharts();
    if (state.route !== "map" && state.map) { state.map.remove(); state.map = null; }
    setTitle();
    const v = document.getElementById("view");
    v.className = "";
    v.onclick = null;
    document.body.classList.toggle("drive-mode", state.route === "drive");
    if (state.route !== "drive") releaseWake();
    const fn = { home: renderHome, footage: renderFootage, starlink: renderStarlink, map: renderMap, pi: renderPi, settings: renderSettings, activity: renderActivity, drive: renderDrive }[state.route] || renderHome;
    fn(v);
  }

  // ---------- login ----------
  function renderLogin() {
    $app.innerHTML = `
      <div class="login"><form class="box" id="loginForm" autocomplete="on">
        <div class="logo">${ic("sat")}</div>
        <div><h1 style="font-size:32px">Car Atlas</h1><div class="muted">Your Model Y, Starlink and Pi in one place.</div></div>
        <div class="field"><label for="pw">Password</label>
          <input class="input" id="pw" type="password" autocomplete="current-password" required autofocus></div>
        <div class="err" id="loginErr" role="alert"></div>
        <button class="btn primary block" type="submit">Sign in</button>
        <div class="muted small">You'll stay signed in on this phone for 6 months.</div>
      </form></div>`;
    document.getElementById("loginForm").onsubmit = async (e) => {
      e.preventDefault();
      const errEl = document.getElementById("loginErr");
      errEl.textContent = "";
      try {
        const res = await fetch("/api/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ password: document.getElementById("pw").value, label: isIOS() ? "iPhone" : "Browser" }) });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { errEl.textContent = data.error || "Couldn't sign in."; return; }
        state.authed = true;
        $app.innerHTML = "";
        await boot();
      } catch { errEl.textContent = "No connection. Try again in a moment."; }
    };
  }

  // ---------- HOME ----------
  function chainHtml(D) {
    const { fresh, pi, link, onStarlink } = D;
    const st = (ok, bad) => (!fresh ? "" : ok ? "ok" : bad ? "bad" : "");
    const n1 = fresh ? "ok" : "";
    const n2 = !fresh ? "" : onStarlink ? (link.pi_talking_to_dish ? "ok" : "bad") : (pi.wifi_ssid ? "ok" : "bad");
    const n3 = st(pi.internet, true);
    const n4 = st(D.s && D.s.drive_setup, true);
    const wire = (cls) => `<div class="wire ${cls}"><svg viewBox="0 0 100 10" preserveAspectRatio="none"><line x1="2" y1="5" x2="98" y2="5"/></svg></div>`;
    return `<div class="chain" aria-label="Connection chain">
      <div class="node ${n1}"><div class="ic">${ic("car")}</div>Pi</div>${wire(n1 && n2 ? n2 : "")}
      <div class="node ${n2}"><div class="ic">${ic(onStarlink || !fresh ? "sat" : "wifi")}</div>${onStarlink || !fresh ? "Starlink" : "WiFi"}</div>${wire(n2 === "ok" ? n3 : "")}
      <div class="node ${n3}"><div class="ic">${ic("globe")}</div>Internet</div>${wire(n3 === "ok" ? n4 : "")}
      <div class="node ${n4}"><div class="ic">${ic("drive")}</div>Drive</div>
    </div>`;
  }

  function setupItems(D) {
    const ov = state.ov || {};
    const items = [];
    items.push({ done: !!ov.paired, t: "Connect the Pi", d: "Install Car Atlas on the Pi and link it to this app.", go: "#settings" });
    items.push({ done: !!(D.s && D.s.drive_setup), t: "Connect Google Drive", d: "So clips can upload. One-time step on the Pi.", go: "#settings" });
    items.push({ done: !!(D.s && (D.carOk || D.usb.ever_connected)), t: "Car cable in the Pi's USB0 port", d: "Glovebox USB port → Pi's USB0 (the USB-C at the end of the board, next to the antenna). Take the flash drive out. The car records to the Pi once this turns green.", go: "#footage" });
    items.push({ done: state.pushOn === true, t: "Notifications on", d: standalone() ? "Get alerts when clips upload or something needs you." : "Add Car Atlas to your Home Screen first, then turn them on.", go: "#settings" });
    return items;
  }

  function clipCard(c) {
    const d = folderDate(c.folder);
    const img = c.has_thumb ? `<img loading="lazy" alt="" src="/api/clips/${c.id}/thumb">` : ic(c.kind === "sentry" ? "shield" : "film");
    return `<a class="clip" data-clip="${c.id}" href="${esc(c.drive_url || DRIVE[c.kind] || DRIVE.root)}" target="_blank" rel="noopener">
      <div class="thumb">${img}<span class="tag ${esc(c.kind)}">${kindLabel[c.kind] || "Clip"}</span></div>
      <div class="meta"><div class="reason">${esc(reasonText(c))}</div>
      <div class="sub">${esc(friendlyDate(d) || ago(c.uploaded_at))}${c.city ? " · " + esc(c.city) : ""}</div>
      <div class="sub num">${fmtN(c.size_mb, 0, " MB")}</div></div></a>`;
  }

  const CAM_NAMES = { front: "Front", back: "Back", left_repeater: "Left side", right_repeater: "Right side", left_pillar: "Left pillar", right_pillar: "Right pillar" };
  function clipSheet(c) {
    let files = [];
    try { files = JSON.parse(c.files || "[]") || []; } catch { files = []; }
    const minutes = [...new Set(files.map((f) => f[0]))];
    // Open on the minute the event happened in (Tesla saves about 10 minutes leading up to it).
    let pick = minutes[0];
    if (c.event_ts) { const key = String(c.event_ts).replace("T", "_").replace(/:/g, "-").slice(0, 19); pick = minutes.find((m) => m <= key) || pick; }
    const d = folderDate(c.folder);
    const minuteLabel = (m) => { const x = folderDate(m); return x ? x.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) : m; };
    const camsFor = (m) => files.filter((f) => f[0] === m).map((f) => `<a class="btn" href="https://drive.google.com/file/d/${esc(f[2])}/view" target="_blank" rel="noopener">${esc(CAM_NAMES[f[1]] || f[1])}</a>`).join("");
    sheet(`<h2>${esc(reasonText(c))}</h2>
      <div class="muted">${esc(friendlyDate(d) || ago(c.uploaded_at))}${c.city ? " · " + esc(c.city) : ""} · ${esc(gbText(c.size_mb || 0))}${c.network ? ` · sent over ${c.network === "starlink" ? "Starlink" : c.network === "home" ? "home WiFi" : "WiFi"}` : ""}</div>
      ${c.has_thumb ? `<img class="clip-thumb" alt="" src="/api/clips/${c.id}/thumb">` : ""}
      ${minutes.length ? `<div><div class="small muted" style="margin-bottom:6px">Jump straight to a camera</div>
        ${minutes.length > 1 ? `<div class="chips scroll" id="minPick">${minutes.slice(0, 12).map((m) => `<button class="chip ${m === pick ? "on" : ""}" data-min="${esc(m)}">${esc(minuteLabel(m))}</button>`).join("")}</div>` : ""}
        <div class="cams" id="camBtns">${camsFor(pick)}</div></div>` : ""}
      <div class="row">
        <a class="btn primary" style="flex:1" href="${esc(c.drive_url || DRIVE[c.kind] || DRIVE.root)}" target="_blank" rel="noopener">${ic("drive")} Open folder in Drive</a>
        ${c.lat !== null && c.lat !== undefined ? `<a class="btn" style="flex:1" href="https://maps.apple.com/?ll=${c.lat},${c.lon}&q=${encodeURIComponent(reasonText(c))}" target="_blank" rel="noopener">${ic("pin")} Where</a>` : ""}
      </div>`, (el) => {
      el.querySelectorAll("[data-min]").forEach((b) => b.onclick = () => {
        el.querySelectorAll("[data-min]").forEach((x) => x.classList.toggle("on", x === b));
        el.querySelector("#camBtns").innerHTML = camsFor(b.dataset.min);
      });
    });
  }

  function renderHome(v) {
    const D = derive();
    const ov = state.ov || {};
    const q = qualityBars(D.d, D.fresh && D.onStarlink);
    const cam = D.cam;
    const camLevel = !D.s ? "" : cam.gadget === "attached" ? (D.carOk || !D.fresh ? "ok" : "bad") : cam.gadget === "unsupported" || cam.gadget === "error" ? "bad" : "warn";
    const temp = D.pi.cpu_temp_c;
    const tempLevel = !D.fresh ? "" : temp >= 80 ? "bad" : temp >= 70 ? "warn" : "ok";
    const today = ov.today || {};
    const setup = setupItems(D);
    const left = setup.filter((s) => !s.done);
    const lastClip = (ov.clips || [])[0];
    const pend = cam.pending || {};
    const pendingN = (pend.dashcam || 0) + (pend.sentry || 0);

    v.className = "two";
    v.innerHTML = `
      <section class="card hero ${D.level} wide">
        <div class="row between"><span class="greet">${esc(greet())}${D.fresh && D.motion ? (D.motion.driving ? ` · <span class="num">${fmtN(D.motion.speed_mph, 0)}</span> mph` : " · Parked") : ""}</span>
          <span class="pill ${D.level === "idle" ? "" : D.level} ${D.fresh ? "live" : ""}">${D.fresh ? "Live" : "Offline"}</span></div>
        <div class="headline">${esc(D.headline)}</div>
        ${chainHtml(D)}
        <div class="note">${esc(D.note)}</div>
        ${worksNow(D).length ? `<div class="caps">${worksNow(D).map(([t, l]) => `<span class="cap ${l}">${ic(l === "ok" ? "check" : "alert")}${esc(t)}</span>`).join("")}${D.onStarlink && D.d.devices ? `<span class="cap">${ic("users")}${D.d.devices.count} on the car WiFi</span>` : ""}</div>` : ""}
      </section>

      ${todayCard(D)}

      <section class="tiles wide">
        <a class="tile ${camLevel}" href="#footage"><span class="stripe"></span>
          <span class="k">${ic("rec")} Dashcam</span>
          <span class="v">${!D.s ? "—" : cam.gadget === "attached" ? (D.carOk ? "Recording" : D.fresh ? "Not connected" : "Ready") : cam.gadget === "unsupported" ? "Not working" : "Checking"}</span>
          <span class="s">${cam.uploading ? "Uploading now" : pendingN ? `${pendingN} waiting to upload` : `${(ov.counts && (ov.counts.dashcam || 0) + (ov.counts.sentry || 0)) || 0} clips in Drive`}</span></a>
        <a class="tile ${!D.fresh || !D.onStarlink ? "" : q >= 3 ? "ok" : q === 2 ? "warn" : "bad"}" href="#starlink"><span class="stripe"></span>
          <span class="k">${ic("sat")} Starlink</span>
          <span class="v">${D.fresh && D.onStarlink ? `${barsHtml(q)} <span class="num" style="font-size:20px">${fmtN(D.d.ping_ms, 0)}</span><span class="small muted"> ms</span>` : "—"}</span>
          <span class="s">${D.fresh ? (D.onStarlink ? (D.d.state === "CONNECTED" ? "Connected" : esc(D.d.state || "Searching")) : "Pi on " + esc(D.pi.wifi_ssid || "no WiFi")) : "Asleep"}</span></a>
        <a class="tile ${tempLevel}" href="#pi"><span class="stripe"></span>
          <span class="k">${ic("therm")} Pi temp</span>
          <span class="v num">${D.fresh ? fmtN(temp, 0, "°C") : "—"}</span>
          <span class="s">${D.fresh ? (temp >= 80 ? "Hot! Check the glovebox" : temp >= 70 ? "Warm" : "Cool and happy") : "Off while the car sleeps"}</span></a>
        <a class="tile" href="#starlink"><span class="stripe"></span>
          <span class="k">${ic("data")} ${ov.plan ? "Data plan" : "Data today"}</span>
          <span class="v num">${ov.plan ? `${ov.plan.pct}%` : today.down_mb !== undefined && today.down_mb !== null ? gbText((today.down_mb || 0) + (today.up_mb || 0)) : "—"}</span>
          <span class="s">${ov.plan ? `${ov.plan.used_gb} of ${ov.plan.gb} GB this month` : today.clips_mb ? `${fmtN(today.clips_mb, 0)} MB was footage` : "Starlink usage"}</span></a>
      </section>

      <section class="actions six wide">
        <button class="btn" id="qaSave">${ic("save")}Save last<br>10 min</button>
        <button class="btn" id="qaSpeed">${ic("gauge")}Speed<br>test</button>
        <button class="btn" id="qaWifi">${ic("qr")}Share<br>WiFi</button>
        <a class="btn" href="#drive">${ic("wheel")}Drive<br>mode</a>
        <button class="btn" id="qaCheck">${ic("pulse")}Health<br>check</button>
        <button class="btn" id="qaDish">${ic("power")}Restart<br>Starlink</button>
      </section>

      ${left.length ? `<section class="card wide"><div class="card-head"><h2>Finish setup</h2><span class="pill accent">${setup.length - left.length} of ${setup.length} done</span></div>
        <div class="steps">${setup.map((s, i) => `<a class="step ${s.done ? "done" : ""}" href="${s.go}" style="text-decoration:none;color:inherit">
          <span class="n">${s.done ? ic("check", 'style="width:16px;height:16px"') : i + 1}</span>
          <span><div class="t">${esc(s.t)}</div>${s.done ? "" : `<div class="d">${esc(s.d)}</div>`}</span></a>`).join("")}</div></section>` : ""}

      ${(() => { const V = verInfo(); return V.behind ? `<a class="banner warn wide" href="#pi" style="text-decoration:none;color:inherit">${ic("save")}<div><b>Pi update waiting.</b> It's on v${esc(V.pi)}, newest is v${esc(V.latest)}. ${esc(V.fresh ? "Should land in a few minutes." : "Lands next time the car is awake.")}</div></a>` : ""; })()}

      <section class="card">
        <div class="card-head"><h2>Latest footage</h2><a class="small" href="#footage">See all</a></div>
        ${lastClip ? `<div class="clips" style="grid-template-columns:1fr">${clipCard(lastClip)}</div>` :
          `<div class="empty">${ic("film")}<div>No clips yet. Saved dashcam clips and Sentry events show up here after they upload.</div></div>`}
      </section>

      <section class="card">
        <div class="card-head"><h2>Activity</h2><a class="small" href="#activity">See all</a></div>
        ${alertsList((ov.alerts || []).slice(0, 5))}
      </section>`;

    document.getElementById("qaSave").onclick = () => saveRecentSheet();
    document.getElementById("qaDish").onclick = () => runCommand("restart_dish");
    document.getElementById("qaSpeed").onclick = () => runSpeedTest();
    document.getElementById("qaWifi").onclick = () => wifiSheet();
    document.getElementById("qaCheck").onclick = () => runDiagnostic("doctor");
    v.querySelectorAll("[data-clip]").forEach((a) => a.onclick = (e) => { e.preventDefault(); const c = (ov.clips || []).find((x) => String(x.id) === a.dataset.clip); if (c) clipSheet(c); });
  }

  // Today at a glance (plus the last 7 days in one line)
  function todayCard(D) {
    const ov = state.ov || {};
    const t = ov.today || {}, w = ov.week || {}, drops = ov.drops_today || {};
    if (!ov.status_at) return "";
    const goodPct = (o) => (o.starlink_s > 120 ? Math.round((100 * (o.good_s || 0)) / o.starlink_s) : null);
    const wh = t.energy_wh || 0;
    const cell = (k, v, sub) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div>${sub ? `<div class="s">${sub}</div>` : ""}</div>`;
    const gp = goodPct(t), wgp = goodPct(w);
    return `<section class="card wide">
      <div class="card-head"><h2>Today</h2>${ov.session ? `<span class="pill ok live">Awake ${esc(durShort(ov.server_time - ov.session.start))}</span>` : `<span class="muted small">${esc(new Date().toLocaleDateString([], { weekday: "long" }))}</span>`}</div>
      <div class="stats three">
        ${cell("Car awake", t.awake_s ? durShort(t.awake_s) : "—")}
        ${cell("Starlink good", gp === null ? "—" : gp + "%", drops.count ? `${drops.count} drop${drops.count === 1 ? "" : "s"} · ${durShort(drops.seconds)}` : gp === null ? "" : "no drops")}
        ${cell("Data used", t.down_mb || t.up_mb ? gbText((t.down_mb || 0) + (t.up_mb || 0)) : "—")}
        ${cell("Clips saved", ov.clips_today || 0)}
        ${cell("Starlink power", wh ? (wh >= 1000 ? (wh / 1000).toFixed(2) + " kWh" : Math.round(wh) + " Wh") : "—", wh ? `about ${(wh / 10 / BATTERY_KWH).toFixed(wh / 10 / BATTERY_KWH < 1 ? 2 : 1)}% of the battery` : "")}
        ${cell("Speed", ov.speedtest_last ? `${Math.round(ov.speedtest_last.down)} Mbps` : "—", ov.speedtest_last ? `tested ${ago(ov.speedtest_last.at)}` : "no test yet")}
      </div>
      ${w.awake_s ? `<div class="muted small">Last 7 days: awake ${esc(durShort(w.awake_s))}${wgp !== null ? ` · Starlink good ${wgp}%` : ""} · ${esc(gbText(w.data_mb || 0))} · ${w.drops || 0} drop${w.drops === 1 ? "" : "s"}${w.energy_wh ? ` · ${(w.energy_wh / 1000).toFixed(1)} kWh` : ""}</div>` : ""}
    </section>`;
  }

  // ---------- speed test ----------
  async function runSpeedTest() {
    const D = derive();
    if (D.fresh && D.d.speedtest_running) { toast("A speed test is already running."); return; }
    const yes = await confirmSheet({ title: "Run a speed test?", body: `The Pi measures download, upload and ping on ${D.fresh && !D.onStarlink ? "the WiFi it's on right now" : "the Starlink"}. It takes about 20 seconds and uses around 75 MB of data.${D.fresh ? "" : " The car is asleep, so it runs the next time the Pi is on."}`, yes: "Run it" });
    if (!yes) return;
    try {
      const r = await api("/api/commands", { method: "POST", body: { type: "speedtest" } });
      toast(r.note || (D.fresh ? "Running. The result shows up here in about half a minute." : "Queued for the next time the car is awake."));
      watchCommand(r.id);
    } catch (e) { if (e.message !== "auth") toast(e.message); }
  }
  // Keep an eye on something we just asked the Pi to do, so the screen updates the moment it's done.
  function watchCommand(id, onDone) {
    let tries = 0;
    clearInterval(state.cmdTimer);
    state.cmdTimer = setInterval(async () => {
      tries++;
      try {
        const r = await api(`/api/commands/${id}`);
        const c = r.command;
        if (["done", "failed", "expired", "cancelled"].includes(c.status)) {
          clearInterval(state.cmdTimer);
          await refresh();
          if (onDone) onDone(c, r.label); else if (c.result) toast(c.result, 6000);
          if (!document.querySelector(".scrim")) render();
        }
      } catch { /* keep waiting */ }
      if (tries > 40) clearInterval(state.cmdTimer);
    }, 4000);
  }

  // ---------- diagnostics (what you used to need SSH for) ----------
  async function runDiagnostic(type) {
    const D = derive();
    try {
      const r = await api("/api/commands", { method: "POST", body: { type } });
      toast(D.fresh ? "Asked the Pi. The report opens here when it's ready (under a minute)." : "The car is asleep. The report will be waiting in the Pi tab after the next drive.", 5000);
      watchCommand(r.id, (c, label) => { if (c.output) outputSheet(c, label); else toast(c.result || "Done"); });
    } catch (e) { if (e.message !== "auth") toast(e.message); }
  }
  function outputSheet(c, label) {
    sheet(`<h2>${esc(label || "Report")}</h2><div class="muted small">${esc(friendlyDate(new Date((c.done || c.created) * 1000)))}</div>
      <pre class="report">${esc(c.output || "")}</pre>
      <div class="row"><button class="btn" style="flex:1" data-copy>${ic("copy")} Copy</button><button class="btn primary" style="flex:1" data-close>Close</button></div>`, (el, close) => {
      el.querySelector("[data-close]").onclick = close;
      el.querySelector("[data-copy]").onclick = () => copyText(c.output || "");
    });
  }
  async function openCommandOutput(id) {
    try { const r = await api(`/api/commands/${id}`); outputSheet(r.command, r.label); } catch (e) { if (e.message !== "auth") toast(e.message); }
  }

  // ---------- share the car WiFi ----------
  function wifiQrSvg(ssid, password) {
    if (typeof qrcode === "undefined") return "";
    const q = (v) => String(v).replace(/([\\;,:"])/g, "\\$1");
    const qr = qrcode(0, "M");
    qr.addData(`WIFI:T:${password ? "WPA" : "nopass"};S:${q(ssid)};${password ? `P:${q(password)};` : ""};`);
    qr.make();
    const n = qr.getModuleCount();
    let path = "";
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (qr.isDark(y, x)) path += `M${x + 2},${y + 2}h1v1h-1z`;
    return `<svg class="qr" viewBox="0 0 ${n + 4} ${n + 4}" role="img" aria-label="QR code to join ${esc(ssid)}"><rect width="100%" height="100%" fill="#fff"/><path d="${path}" fill="#000"/></svg>`;
  }
  async function wifiSheet(edit) {
    let w = null;
    try { w = (await api("/api/settings/wifi")).wifi; } catch (e) { if (e.message === "auth") return; }
    if (!w || edit) {
      const ssid = (w && w.ssid) || "JonesyStarlink";
      sheet(`<h2>Share the car WiFi</h2><div class="muted">Type the Starlink WiFi name and password once. After that, anyone in the car can point their camera at the code and join. It's kept in your private Car Atlas account.</div>
        <form id="wifiForm" class="steps">
          <div class="field"><label for="wSsid">WiFi name</label><input class="input" id="wSsid" value="${esc(ssid)}" required autocapitalize="off" autocorrect="off"></div>
          <div class="field"><label for="wPass">Password</label><input class="input" id="wPass" value="${esc((w && w.password) || "")}" autocapitalize="off" autocorrect="off" autocomplete="off"></div>
          <button class="btn primary block" type="submit">Save and show the code</button>
        </form>`, (el, close) => {
        el.querySelector("#wifiForm").onsubmit = async (e) => {
          e.preventDefault();
          try {
            await api("/api/settings/wifi", { method: "POST", body: { ssid: el.querySelector("#wSsid").value.trim(), password: el.querySelector("#wPass").value } });
            if (state.ov) state.ov.wifi_set = true;
            close(); wifiSheet();
          } catch (er) { if (er.message !== "auth") toast(er.message); }
        };
      });
      return;
    }
    sheet(`<h2>Join the car WiFi</h2>
      <div class="qr-wrap">${wifiQrSvg(w.ssid, w.password) || `<div class="muted">Couldn't draw the code. Check your connection and try again.</div>`}</div>
      <div style="text-align:center"><div style="font-weight:600">${esc(w.ssid)}</div><div class="num muted">${esc(w.password || "No password")}</div></div>
      <div class="muted small" style="text-align:center">Point a phone camera at the code and tap “Join”.</div>
      <div class="row"><button class="btn" style="flex:1" data-copy>${ic("copy")} Copy password</button><button class="btn ghost" style="flex:1" data-edit>Change</button></div>`, (el, close) => {
      el.querySelector("[data-copy]").onclick = () => copyText(w.password || "");
      el.querySelector("[data-edit]").onclick = () => { close(); wifiSheet(true); };
    });
  }

  function alertsList(alerts) {
    if (!alerts.length) return `<div class="empty">${ic("bell")}<div>Nothing yet. Uploads, warnings and fixes show up here.</div></div>`;
    return `<ul class="list">${alerts.map((a) => `<li class="item"><span class="dot ${esc(a.category)}"></span>
      <div class="body"><div class="t">${esc(a.title)}</div><div class="m">${esc(a.message)}</div></div>
      <span class="when">${esc(ago(a.at))}</span></li>`).join("")}</ul>`;
  }

  // ---------- commands ----------
  const CMD_COPY = {
    upload_recent: { title: "Save recent dashcam", ok: "Sent! The Pi grabs it next time it checks in (within a minute while the car is awake)." },
    restart_dish: { title: "Restart Starlink?", body: "Internet in the car drops for about 2 minutes while the dish restarts. Use this if it seems stuck.", yes: "Restart it", ok: "Sent. The Starlink restarts once the Pi picks this up." },
    update_now: { ok: "Sent. The Pi checks GitHub for updates in a moment." },
    restart_services: { title: "Restart Pi services?", body: "Restarts the uploader and monitor. The dashcam keeps recording.", yes: "Restart", ok: "Sent." },
    reboot_pi: { title: "Restart the Pi?", body: "The dashcam drive disappears for about a minute while the Pi restarts, so the car can't record during that time. Best done while parked.", yes: "Restart the Pi", danger: true, ok: "Sent. The Pi restarts when it picks this up." },
    test_alert: { ok: "Sent. You'll get a test alert from the Pi in a moment." },
    usb_rebind: { ok: "Sent. The Pi re-offers the drive to the car (like unplugging and plugging it back in)." },
    usb_fix: { title: "Try the fallback USB mode?", body: "Only if the cable is already in USB0 and the car still won't connect. The Pi switches USB0 to a different mode and restarts (about 2 minutes, dashcam paused). You can undo it from here.", yes: "Switch and restart", danger: true, ok: "Sent. The Pi restarts with the new USB setting." },
    usb_fix_undo: { title: "Undo the USB fallback?", body: "Puts USB0 back to the normal setting and restarts the Pi (about 2 minutes).", yes: "Undo and restart", ok: "Sent. The Pi restarts with the normal USB setting." },
  };
  async function runCommand(type, args) {
    const c = CMD_COPY[type] || {};
    if (c.title && type !== "upload_recent") {
      const yes = await confirmSheet({ title: c.title, body: esc(c.body || ""), yes: c.yes || "Do it", danger: c.danger });
      if (!yes) return;
    }
    try {
      const r = await api("/api/commands", { method: "POST", body: { type, args } });
      toast(r.note || c.ok || "Sent");
      refresh();
    } catch (e) { if (e.message !== "auth") toast(e.message); }
  }
  function saveRecentSheet() {
    let minutes = 10;
    sheet(`<h2>Save recent dashcam</h2>
      <div class="muted">The car keeps about the last hour of driving. Pick how far back to send to Google Drive.</div>
      <div class="chips" id="minChips">${[5, 10, 20, 30, 60].map((m) => `<button class="chip ${m === 10 ? "on" : ""}" data-m="${m}">${m} min</button>`).join("")}</div>
      <button class="btn primary block" id="goSave">${ic("upload")} Upload last <span id="minLbl">10</span> min</button>
      <div class="muted small">Each minute is roughly 150–250 MB across all cameras. Over Starlink that takes a while, so pick only what you need. It's fastest at home.</div>`, (el, close) => {
      el.querySelectorAll("[data-m]").forEach((b) => b.onclick = () => {
        minutes = Number(b.dataset.m);
        el.querySelectorAll("[data-m]").forEach((x) => x.classList.toggle("on", x === b));
        el.querySelector("#minLbl").textContent = minutes;
      });
      el.querySelector("#goSave").onclick = async () => { close(); await runCommand("upload_recent", { minutes }); };
    });
  }
  function cmdStatus(c) {
    const map = { queued: ["Waiting for the Pi", ""], picked: ["Pi is working on it", "accent"], done: ["Done", "ok"], failed: ["Didn't work", "bad"], expired: ["Expired", ""], cancelled: ["Cancelled", ""] };
    return map[c.status] || [c.status, ""];
  }
  function commandsList(cmds, labels) {
    if (!cmds.length) return `<div class="muted small">Nothing sent to the Pi yet.</div>`;
    return `<ul class="list">${cmds.map((c) => {
      const [txt, cls] = cmdStatus(c);
      let args = {}; try { args = JSON.parse(c.args || "{}"); } catch {}
      const lbl = (labels && labels[c.type]) || c.type;
      return `<li class="item"><div class="body"><div class="t">${esc(lbl)}${args.minutes ? ` (${args.minutes} min)` : ""}</div>
        <div class="m">${esc(c.result || ago(c.created))}</div></div>${c.has_output ? `<button class="chip" data-out="${c.id}">Read</button>` : `<span class="pill ${cls}">${esc(txt)}</span>`}</li>`;
    }).join("")}</ul>`;
  }

  // ---------- dashcam USB connection ----------
  function boardSvg(highlight) {
    // Orange Pi Zero 2W, top view. Ports along the bottom edge: mini-HDMI, USB1 (middle), USB0 (end, by the antenna).
    const hl = highlight ? "var(--bad)" : "var(--ok)";
    return `<svg class="board" viewBox="0 0 340 170" role="img" aria-label="Orange Pi Zero 2W: the car's cable goes in USB0, the USB-C port at the end of the board next to the antenna">
      <rect x="20" y="22" width="300" height="104" rx="12" fill="color-mix(in srgb, var(--ok) 14%, var(--surface-2))" stroke="var(--line)" stroke-width="2"/>
      <g fill="var(--muted)" opacity=".55">${Array.from({ length: 20 }, (_, i) => `<circle cx="${52 + i * 12.4}" cy="34" r="2.2"/><circle cx="${52 + i * 12.4}" cy="44" r="2.2"/>`).join("")}</g>
      <rect x="138" y="62" width="44" height="44" rx="4" fill="var(--ink)" opacity=".75"/>
      <text x="160" y="88" text-anchor="middle" font-size="9" fill="var(--surface)" font-family="IBM Plex Mono, monospace">CPU</text>
      <rect x="22" y="62" width="26" height="34" rx="3" fill="var(--surface)" stroke="var(--line)"/>
      <text x="35" y="112" text-anchor="middle" font-size="9" fill="var(--muted)">SD</text>
      <circle cx="304" cy="62" r="6" fill="#c9a227" stroke="var(--line)"/>
      <text x="304" y="82" text-anchor="middle" font-size="9" fill="var(--muted)">antenna</text>
      <rect x="70" y="114" width="40" height="16" rx="3" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.5"/>
      <rect x="196" y="114" width="30" height="14" rx="7" fill="var(--surface)" stroke="var(--muted)" stroke-width="1.5"/>
      <rect class="port-hl" x="258" y="112" width="34" height="18" rx="9" fill="${hl}" opacity=".25"/>
      <rect x="260" y="114" width="30" height="14" rx="7" fill="var(--surface)" stroke="${hl}" stroke-width="2.5"/>
      <text x="90" y="148" text-anchor="middle" font-size="11" fill="var(--muted)">mini-HDMI</text>
      <text x="211" y="148" text-anchor="middle" font-size="11" fill="var(--muted)">USB1</text>
      <text x="211" y="162" text-anchor="middle" font-size="9.5" fill="var(--muted)">GPS (optional)</text>
      <text x="275" y="148" text-anchor="middle" font-size="12" font-weight="700" fill="${hl}">USB0</text>
      <text x="275" y="162" text-anchor="middle" font-size="9.5" font-weight="600" fill="${hl}">car cable</text>
      <path d="M275 6v12" stroke="${hl}" stroke-width="2.5" stroke-linecap="round"/><path d="M269 12l6 6 6-6" fill="none" stroke="${hl}" stroke-width="2.5" stroke-linecap="round"/>
    </svg>`;
  }
  function usbCard(D) {
    if (!D.s) return "";
    const u = D.usb, carOk = D.carOk;
    const stateTxt = { configured: "Connected", "not attached": "Nothing plugged in", attached: "Plugged in, starting", powered: "Powered, no data yet", default: "Talking, not finished", addressed: "Almost connected", suspended: "Car asleep" }[u.state] || u.state || "Unknown";
    const showFix = D.fresh && !carOk;
    return `<section class="card wide">
      <div class="card-head"><h2>Car connection</h2><span class="pill ${!D.fresh ? "" : carOk ? "ok" : "bad"}">${!D.fresh ? "Offline" : carOk ? "Connected" : "Not connected"}</span></div>
      ${boardSvg(D.fresh && !carOk)}
      ${D.fresh && !carOk ? `<div class="banner bad">${ic("usb")}<div>${esc(u.hint || "The car isn't connected to the Pi's USB0 port.")}</div></div>
        <div class="steps">
          <div class="step"><span class="n">1</span><span><div class="t">Glovebox USB port → Pi's USB0</div><div class="d">USB0 is the USB-C at the end of the board, next to the gold antenna connector. Only one thing fits that glovebox port, so the flash drive comes out.</div></span></div>
          <div class="step"><span class="n">2</span><span><div class="t">Use a data cable</div><div class="d">Some USB-C cables only charge. If it still won't connect, swap the cable.</div></span></div>
          <div class="step"><span class="n">3</span><span><div class="t">Wake the car and wait a minute</div><div class="d">The Pi re-offers the drive on its own once. This card turns green when the car connects.</div></span></div>
        </div>` : carOk ? `<div class="muted small">The car sees the Pi as its dashcam drive${u.speed && u.speed !== "UNKNOWN" ? ` (${esc(u.speed)})` : ""}. Leave the flash drive out.</div>` : `<div class="muted small">Status shows once the car is awake and the Pi checks in.</div>`}
      <dl class="kv">
        <dt>USB link</dt><dd>${esc(stateTxt)}</dd>
        <dt>Drive offered</dt><dd>${u.bound ? "Yes" : "No"}${u.rebind_tried ? " · retried once" : ""}</dd>
        <dt>USB0 mode</dt><dd>${esc(u.dr_mode || "—")}${u.otg_fix_installed ? " · fallback on" : ""}</dd>
        <dt>Drive size</dt><dd>${u.image_gb ? fmtN(u.image_gb, 0, " GB") : "—"}</dd>
        <dt>Ever connected</dt><dd>${u.ever_connected ? "Yes" : "Not yet"}</dd>
      </dl>
      ${u.usb0_host_overlay ? `<div class="banner bad">${ic("alert")}<div>USB0 is set to host mode in orangepi-config (usb0-host). That blocks the car. Turn it off in orangepi-config → System → Hardware.</div></div>` : ""}
      <div class="row">
        <button class="btn" style="flex:1" data-cmd="usb_rebind">${ic("refresh")} Re-offer drive</button>
        ${u.otg_fix_installed ? `<button class="btn" style="flex:1" data-cmd="usb_fix_undo">Undo fallback</button>` : showFix && u.ever_connected === false ? `<button class="btn ghost" style="flex:1" data-cmd="usb_fix">Try fallback mode</button>` : ""}
      </div>
      ${(u.image_gb || 0) && u.image_gb < 60 ? `<div class="muted small">Tesla suggests a 64 GB+ drive. This one is ${fmtN(u.image_gb, 0)} GB, sized to fit your SD card. A 128 GB high-endurance microSD in the Pi gives you a full-size drive.</div>` : ""}
    </section>`;
  }

  // ---------- FOOTAGE ----------
  async function loadClips(reset) {
    if (reset) { state.clips = null; state.clipsDone = false; }
    const before = state.clips && state.clips.length ? state.clips[state.clips.length - 1].id : "";
    const r = await api(`/api/clips?kind=${state.footKind}&limit=24${before ? "&before=" + before : ""}`);
    state.clips = (state.clips || []).concat(r.clips);
    state.clipsDone = r.clips.length < 24;
  }
  function renderFootage(v) {
    const D = derive();
    const ov = state.ov || {};
    const cam = D.cam;
    const img = cam.image || {};
    const pend = cam.pending || {};
    const counts = ov.counts || {};
    const reqs = (ov.commands || []).filter((c) => c.type === "upload_recent").slice(0, 3);
    let status, cls = "";
    if (!D.s) status = "Waiting for the Pi to check in.";
    else if (cam.gadget === "unsupported") { status = "This Pi can't act as a USB drive yet, so the car is NOT saving footage to it. Keep a flash drive in the glovebox port."; cls = "bad"; }
    else if (cam.gadget === "error") { status = "The dashcam drive hit a problem: " + (cam.detail || "unknown") + "."; cls = "bad"; }
    else if (cam.uploading) {
      const up = cam.uploading;
      status = `Uploading ${up.kind === "sentry" ? "a Sentry event" : "a dashcam clip"} (${gbText(up.mb)})${up.pct ? ` · ${up.pct}%` : ""}${up.eta_s ? ` · about ${durShort(up.eta_s)} left` : ""}${up.kbps ? ` · ${(up.kbps / 1000).toFixed(1)} Mbps` : ""}`;
    }
    else if (cam.waiting_for) { status = "Clips are waiting for " + cam.waiting_for + "."; cls = "warn"; }
    else if (cam.gadget === "attached" && !D.carOk && D.fresh) { status = "The Pi is offering the drive, but the car hasn't connected to it. See “Car connection” below."; cls = "bad"; }
    else status = cam.gadget === "attached" ? (D.carOk ? "Car is recording to the Pi. Saved clips and Sentry events upload on their own." : "Ready. Saved clips and Sentry events upload on their own.") : "Checking the dashcam drive…";

    v.className = "two";
    v.innerHTML = `
      <section class="card wide">
        <div class="card-head"><h2>Dashcam drive</h2>
          <span class="pill ${cam.gadget === "attached" ? (D.carOk || !D.fresh ? "ok" : "bad") : cam.gadget === "unsupported" || cam.gadget === "error" ? "bad" : ""}">${cam.gadget === "attached" ? (D.carOk ? "Car connected" : D.fresh ? "Car not connected" : "Ready") : cam.gadget === "unsupported" ? "Not supported" : D.s ? "Checking" : "Offline"}</span></div>
        <div class="banner ${cls}">${ic(cls === "bad" ? "alert" : cam.uploading ? "upload" : "rec")}<div>${esc(status)}</div></div>
        ${cam.uploading ? (cam.uploading.pct ? `<div class="meter"><span style="width:${cam.uploading.pct}%;background:var(--accent)"></span></div>` : `<div class="meter indet"><span></span></div>`) : ""}
        ${D.fresh && D.carOk ? `<div class="row small" style="gap:8px"><span class="dot ${D.usb.writing ? "rec-on" : ""}" style="background:${D.usb.writing ? "var(--bad)" : "var(--line)"}"></span><span class="muted">${D.usb.writing ? `The car is writing video to the Pi (last write ${esc(ago(D.usb.last_write_epoch))})` : D.usb.last_write_epoch ? `Car connected. Last video written ${esc(ago(D.usb.last_write_epoch))}` : "Car connected"}${D.usb.drops ? ` · connection reset ${D.usb.drops}× since the Pi turned on` : ""}</span></div>` : ""}
        <div class="stats">
          <div class="stat"><div class="k">Waiting</div><div class="v">${pend.dashcam || 0} dash · ${pend.sentry || 0} sentry</div>${cam.pending_mb ? `<div class="s">${esc(gbText(cam.pending_mb))}${D.onStarlink && cam.bwlimit && cam.bwlimit !== "0" ? ` · about ${esc(durShort(cam.pending_mb * 1e6 / ({ "190k": 190e3, "375k": 375e3, "1M": 1e6 }[cam.bwlimit] || 375e3)))} on Starlink` : ""}</div>` : ""}</div>
          <div class="stat"><div class="k">In Drive</div><div class="v">${(counts.dashcam || 0) + (counts.sentry || 0) + (counts.requested || 0)} clips</div></div>
          <div class="stat"><div class="k">Uploaded</div><div class="v">${fmtN((counts.total_mb || 0) / 1000, 1, " GB")}</div></div>
          <div class="stat"><div class="k">Over Starlink today</div><div class="v">${fmtN(cam.starlink_uploaded_today_mb, 0, " MB")}</div></div>
        </div>
        <div><div class="row between small"><span class="muted">Drive space on the Pi</span><span class="num">${img.used_pct !== undefined ? `${img.used_pct}% used · ${img.free_gb} of ${img.size_gb} GB free` : D.usb.image_gb ? `${D.usb.image_gb} GB drive` : "—"}</span></div>
        <div class="meter" style="margin-top:6px"><span style="width:${img.used_pct || 0}%;background:${(img.used_pct || 0) >= 85 ? "var(--bad)" : (img.used_pct || 0) >= 70 ? "var(--warn)" : "var(--accent)"}"></span></div></div>
      </section>

      ${usbCard(D)}

      <section class="card">
        <div class="card-head"><h2>Save recent footage</h2></div>
        <div class="muted small">Something happened and you didn't honk or tap save? The car keeps about the last hour.</div>
        <button class="btn primary block" id="fSave">${ic("upload")} Choose how much to save</button>
        ${reqs.length ? commandsList(reqs, ov.command_labels) : ""}
      </section>

      <section class="card">
        <div class="card-head"><h2>Upload rules</h2><span class="pill ${S().uploads_paused ? "warn" : "ok"}">${S().uploads_paused ? "Paused" : "On"}</span></div>
        ${toggleRow("uploads_paused", "Pause all uploads", "Clips stay safe on the Pi and upload when you turn this back off.", S().uploads_paused)}
        ${toggleRow("uploads_on_starlink", "Saved clips over Starlink", "Off = they wait for home WiFi.", S().uploads_on_starlink)}
        ${toggleRow("sentry_on_starlink", "Sentry events over Starlink", "Off = they wait for home WiFi.", S().sentry_on_starlink)}
        <div><div class="small muted" style="margin-bottom:6px">Upload speed on Starlink (lower leaves more for phones)</div>
          ${chipSet("starlink_speed", [["slow", "1.5 Mbps"], ["normal", "3 Mbps"], ["fast", "8 Mbps"], ["max", "No limit"]], S().starlink_speed)}</div>
        <div><div class="small muted" style="margin-bottom:6px">Most footage per day over Starlink</div>
          ${chipSet("starlink_cap_mb", [[1000, "1 GB"], [2000, "2 GB"], [5000, "5 GB"], [10000, "10 GB"], [100000, "No limit"]], S().starlink_cap_mb)}</div>
        <div class="muted small">Home WiFi is always full speed with no limit. “Save recent footage” always goes right away.${ov.settings_applied === false ? " <b>Waiting for the Pi to pick up your last change.</b>" : ""}</div>
      </section>

      <section class="card">
        <div class="card-head"><h2>Google Drive</h2>${D.s && D.s.drive && D.s.drive.free_gb !== null && D.s.drive.free_gb !== undefined ? `<span class="pill ${D.s.drive.free_gb < 5 ? "bad" : D.s.drive.free_gb < 15 ? "warn" : "ok"}">${D.s.drive.free_gb} GB free</span>` : ""}</div>
        ${D.s && D.s.drive && D.s.drive.total_gb ? `<div><div class="row between small"><span class="muted">Drive storage</span><span class="num">${D.s.drive.used_gb} of ${D.s.drive.total_gb} GB used</span></div>
          <div class="meter" style="margin-top:6px"><span style="width:${Math.min(100, Math.round(100 * D.s.drive.used_gb / D.s.drive.total_gb))}%;background:${D.s.drive.free_gb < 5 ? "var(--bad)" : D.s.drive.free_gb < 15 ? "var(--warn)" : "var(--accent)"}"></span></div></div>` : ""}
        <div class="row">
          <a class="btn" style="flex:1" href="${DRIVE.root}" target="_blank" rel="noopener">${ic("drive")} All</a>
          <a class="btn" style="flex:1" href="${DRIVE.dashcam}" target="_blank" rel="noopener">Dashcam</a>
          <a class="btn" style="flex:1" href="${DRIVE.sentry}" target="_blank" rel="noopener">Sentry</a>
        </div>
        <div><div class="small muted" style="margin-bottom:6px">Keep footage in Drive for</div>
          ${chipSet("retention_days", [[0, "Forever"], [30, "30 days"], [90, "90 days"], [180, "6 months"], [365, "1 year"]], S().retention_days || 0, 'data-ctitle="Auto-clear old footage?" data-confirm="Once a day the Pi moves footage older than this out of Google Drive and into Drive\u2019s trash (Google keeps trash for 30 days). Anything you want to keep longer should be moved out of the Tesla Footage folder."')}</div>
        ${cam.retention && cam.retention.files_removed ? `<div class="muted small">Last cleanup ${esc(ago(cam.retention.at))}: ${cam.retention.files_removed} old files moved to Drive trash.</div>` : ""}
      </section>

      <section class="card wide">
        <div class="seg" role="tablist">${["all", "dashcam", "sentry", "requested"].map((k) => `<button role="tab" data-k="${k}" class="${state.footKind === k ? "on" : ""}">${k === "all" ? "All" : kindLabel[k]}</button>`).join("")}</div>
        <div id="clipGrid"><div class="skeleton"></div></div>
        <button class="btn block ghost" id="moreClips" hidden>Load more</button>
      </section>`;

    document.getElementById("fSave").onclick = saveRecentSheet;
    v.querySelectorAll("[data-cmd]").forEach((b) => b.onclick = () => runCommand(b.dataset.cmd));
    bindSettings(v);
    v.onclick = (e) => {
      const a = e.target.closest("[data-clip]");
      if (!a) return;
      e.preventDefault();
      const c = (state.clips || []).concat(ov.clips || []).find((x) => String(x.id) === a.dataset.clip);
      if (c) clipSheet(c);
    };
    v.querySelectorAll("[data-k]").forEach((b) => b.onclick = async () => {
      state.footKind = b.dataset.k;
      v.querySelectorAll("[data-k]").forEach((x) => x.classList.toggle("on", x === b));
      await loadClips(true).catch(() => {});
      drawClips();
    });
    document.getElementById("moreClips").onclick = async () => { await loadClips(false).catch(() => {}); drawClips(); };
    const drawClips = () => {
      const g = document.getElementById("clipGrid");
      if (!g) return;
      const list = state.clips || [];
      g.innerHTML = list.length ? `<div class="clips">${list.map(clipCard).join("")}</div>` :
        `<div class="empty">${ic("film")}<div>${state.footKind === "sentry" ? "No Sentry events yet. When someone comes close to the parked car, the clip lands here." : state.footKind === "requested" ? "Nothing requested yet. Use “Save recent footage” above." : "No clips yet. Honk or tap the dashcam icon to save a clip, and it shows up here after it uploads."}</div></div>`;
      document.getElementById("moreClips").hidden = state.clipsDone || !list.length;
    };
    if (state.clips) drawClips();
    loadClips(true).then(drawClips).catch(() => {});
  }

  // ---------- STARLINK ----------
  function gauge(value, max, label, unit, goodLow = true, warnAt, badAt) {
    const v = value === null || value === undefined || isNaN(value) ? null : Number(value);
    const pct = v === null ? 0 : Math.max(0, Math.min(1, v / max));
    const level = v === null ? "var(--line)" : (goodLow ? (v >= badAt ? "var(--bad)" : v >= warnAt ? "var(--warn)" : "var(--ok)") : "var(--ok)");
    const C = 2 * Math.PI * 42 * 0.75;
    return `<div class="gauge"><svg viewBox="0 0 100 92">
      <circle cx="50" cy="50" r="42" fill="none" stroke="var(--surface-2)" stroke-width="10" stroke-linecap="round" stroke-dasharray="${C} 999" transform="rotate(135 50 50)"/>
      <circle class="arc" cx="50" cy="50" r="42" fill="none" stroke="${level}" stroke-width="10" stroke-linecap="round" stroke-dasharray="${C} 999" stroke-dashoffset="${C * (1 - pct)}" transform="rotate(135 50 50)"/>
      <text x="50" y="54" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="19" fill="var(--ink)">${v === null ? "—" : v < 10 && unit === "%" ? v.toFixed(1) : Math.round(v)}</text>
      <text x="50" y="72" text-anchor="middle" font-size="11" fill="var(--muted)">${unit}</text></svg>
      <div class="lbl">${label}</div></div>`;
  }
  function chartOpts(yTitle, opts = {}) {
    const grid = cssVar("--line"), ink = cssVar("--muted");
    const hours = state.stRange;
    return {
      responsive: true, maintainAspectRatio: false, animation: { duration: 500 },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: !!opts.legend, labels: { color: ink, boxWidth: 10, usePointStyle: true } },
        tooltip: { callbacks: { title: (items) => items.length ? new Date(items[0].parsed.x * 1000).toLocaleString([], { weekday: "short", hour: "numeric", minute: "2-digit" }) : "" } },
      },
      scales: {
        x: { type: "linear", min: (state.ov ? state.ov.server_time : Date.now() / 1000) - hours * 3600, max: state.ov ? state.ov.server_time : Date.now() / 1000, grid: { color: grid }, ticks: { color: ink, maxTicksLimit: 6, stepSize: hours > 48 ? 86400 : hours > 12 ? 4 * 3600 : 3600, callback: (val) => { const d = new Date(val * 1000); return hours > 48 ? d.toLocaleDateString([], { weekday: "short" }) : d.toLocaleTimeString([], { hour: "numeric" }); } } },
        y: { beginAtZero: true, grid: { color: grid }, ticks: { color: ink, maxTicksLimit: 5 }, title: { display: !!yTitle, text: yTitle, color: ink }, ...(opts.y || {}) },
      },
    };
  }
  function lineDs(label, data, color, fill) {
    return { label, data, borderColor: color, backgroundColor: color + "33", fill: !!fill, pointRadius: 0, borderWidth: 2, tension: .3, spanGaps: 300 };
  }
  async function renderStarlink(v) {
    const D = derive();
    const d = D.d;
    const ov = state.ov || {};
    const q = qualityBars(d, D.fresh && D.onStarlink);
    const qText = ["No signal", "Searching", "Weak", "Good", "Great"][q];
    v.className = "two";
    v.innerHTML = `
      <section class="card hero wide">
        <div class="row" style="gap:16px;flex-wrap:nowrap">
          <svg viewBox="0 0 120 120" style="width:86px;flex:none" aria-hidden="true">
            <circle cx="60" cy="60" r="44" fill="none" stroke="var(--line)" stroke-dasharray="3 5"/>
            <g class="orbit"><circle cx="104" cy="60" r="6" fill="var(--beam)"/></g>
            <circle cx="60" cy="60" r="20" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/>
            <path d="M52 66l16-16M60 52h8v8" stroke="var(--accent)" stroke-width="3" fill="none" stroke-linecap="round"/>
          </svg>
          <div style="min-width:0">
            <div class="greet">${D.fresh ? (D.onStarlink ? "Starlink Mini" : "Pi isn't on the Starlink right now") : "Car asleep"}</div>
            <div class="headline">${D.fresh && D.onStarlink ? esc(qText) : "—"}</div>
            <div class="row" style="gap:8px;margin-top:4px">${barsHtml(q)}<span class="muted small">${D.fresh && D.onStarlink ? esc(d.state === "CONNECTED" ? "Connected" : d.state || "") : D.fresh ? "On " + esc(D.pi.wifi_ssid || "no WiFi") : "Last check-in " + ago(state.ov && state.ov.status_at)}</span></div>
          </div>
        </div>
        <div class="gauges">
          ${gauge(D.fresh && D.onStarlink ? d.ping_ms : null, 150, "Ping", "ms", true, 60, 120)}
          ${gauge(D.fresh && D.onStarlink ? d.drop_pct : null, 20, "Dropped", "%", true, 1, 5)}
          ${gauge(D.fresh && D.onStarlink ? d.obstructed_pct : null, 20, "Sky blocked", "%", true, 3, 10)}
        </div>
        ${D.outage ? `<div class="banner bad">${ic("alert")}<div><b>No service for ${esc(durShort(D.outage.seconds))}.</b> Reason: ${esc(D.outage.cause)}.</div></div>` : ""}
        ${worksNow(D).length && D.onStarlink ? `<div class="caps">${worksNow(D).map(([t, l]) => `<span class="cap ${l}">${ic(l === "ok" ? "check" : "alert")}${esc(t)}</span>`).join("")}${d.devices ? `<span class="cap">${ic("users")}${d.devices.count} device${d.devices.count === 1 ? "" : "s"} on the WiFi</span>` : ""}</div>` : ""}
        ${(d.alerts || []).length && D.fresh ? `<div class="banner warn">${ic("alert")}<div>Dish says: ${esc(d.alerts.map((a) => a.replace(/_/g, " ")).join(", "))}</div></div>` : ""}
      </section>

      <section class="card">
        <div class="card-head"><h2>Speed test</h2><span class="muted small">${ov.speedtest_last ? esc(ago(ov.speedtest_last.at)) : ""}</span></div>
        ${ov.speedtest_last ? `<div class="stats three">
          <div class="stat"><div class="k">Download</div><div class="v big">${fmtN(ov.speedtest_last.down, 0)}</div><div class="s">Mbps</div></div>
          <div class="stat"><div class="k">Upload</div><div class="v big">${fmtN(ov.speedtest_last.up, 0)}</div><div class="s">Mbps</div></div>
          <div class="stat"><div class="k">Ping</div><div class="v big">${fmtN(ov.speedtest_last.ping, 0)}</div><div class="s">ms</div></div></div>` :
          `<div class="muted small">No test yet. The Pi runs a small one once a day on Starlink, or tap the button.</div>`}
        <div class="chart-box short"><canvas id="cSpeed"></canvas></div>
        <button class="btn primary block" id="slSpeed" ${D.fresh && d.speedtest_running ? "disabled" : ""}>${ic("gauge")} ${D.fresh && d.speedtest_running ? "Test running…" : "Run speed test"}</button>
        ${toggleRow("auto_speedtest", "Daily automatic test", "One small test a day (about 25 MB) so you can see the trend.", S().auto_speedtest)}
      </section>

      <section class="card">
        <div class="card-head"><h2>Sky view</h2><span class="pill" id="skyPill">—</span></div>
        <div class="sky-wrap"><canvas id="sky" width="246" height="246" aria-label="What the dish can see of the sky"></canvas></div>
        <div class="row small" style="gap:14px;justify-content:center"><span class="row" style="gap:6px"><span class="sw" style="background:var(--beam)"></span>Clear</span><span class="row" style="gap:6px"><span class="sw" style="background:var(--bad)"></span>Blocked</span><span class="row" style="gap:6px"><span class="sw" style="background:var(--surface-2);border:1px solid var(--line)"></span>Not checked yet</span></div>
        <div class="muted small" id="skyNote">This is the dish's own picture of the sky from the back window. Red patches are where the roof, pillars or trees get in the way.</div>
      </section>

      <section class="card wide">
        <div class="card-head"><h2>Drops</h2><span class="pill ${(ov.drops_today || {}).count ? "warn" : "ok"}">${(ov.drops_today || {}).count ? `${ov.drops_today.count} today · ${esc(durShort(ov.drops_today.seconds))}` : "None today"}</span></div>
        <div class="muted small">A drop is 30 seconds or more with no service after the Starlink was already working.</div>
        <h3>Time with a good signal, last 14 days (%)</h3><div class="chart-box short"><canvas id="cGood"></canvas></div>
        <div id="dropList"><div class="skeleton" style="min-height:60px"></div></div>
      </section>

      <section class="card wide">
        <div class="card-head"><h2>History</h2>
          <div class="chips">${[[6, "6h"], [24, "24h"], [168, "7 days"]].map(([h, l]) => `<button class="chip ${state.stRange === h ? "on" : ""}" data-h="${h}">${l}</button>`).join("")}</div></div>
        <h3>Ping (ms)</h3><div class="chart-box"><canvas id="cPing"></canvas></div>
        <h3>Speed in use (Mbps)</h3><div class="chart-box"><canvas id="cThru"></canvas></div>
        <h3>Dropped and blocked (%)</h3><div class="chart-box"><canvas id="cDrop"></canvas></div>
        <div class="muted small" id="histNote"></div>
      </section>

      <section class="card">
        <div class="card-head"><h2>Data used</h2><span class="muted small">last 30 days</span></div>
        <div class="stats" id="usageStats"><div class="stat"><div class="k">Today</div><div class="v">—</div></div></div>
        <div class="chart-box"><canvas id="cUsage"></canvas></div>
        ${ov.plan ? `<div><div class="row between small"><span class="muted">Data plan since ${esc(ov.plan.cycle_start.slice(5).replace("-", "/"))}</span><span class="num">${ov.plan.used_gb} of ${ov.plan.gb} GB · ${ov.plan.pct}%</span></div>
          <div class="meter" style="margin-top:6px"><span style="width:${Math.min(100, ov.plan.pct)}%;background:${ov.plan.pct >= 90 ? "var(--bad)" : ov.plan.pct >= 75 ? "var(--warn)" : "var(--accent)"}"></span></div>
          <div class="muted small" style="margin-top:6px">About ${ov.plan.per_day_gb} GB a day so far. At this pace: ${Math.round(ov.plan.per_day_gb * 30)} GB for the month. Counts what the Pi sees while it's on.</div></div>` : ""}
        <button class="btn block" id="planBtn">${ic("data")} ${ov.plan ? "Change data plan" : "Set a monthly data limit"}</button>
        ${ov.plan ? toggleRow("plan_protect", "Protect the plan", "At 90% used, footage uploads wait for home WiFi.", S().plan_protect) : ""}
      </section>

      <section class="card">
        <div class="card-head"><h2>Dish details</h2></div>
        <dl class="kv">
          <dt>Power draw</dt><dd>${fmtN(d.power_w, 0, " W")}</dd>
          <dt>Energy today</dt><dd>${d.energy_today_wh ? `${Math.round(d.energy_today_wh)} Wh (≈${(d.energy_today_wh / 10 / BATTERY_KWH).toFixed(2)}% battery)` : "—"}</dd>
          <dt>Devices on the WiFi</dt><dd>${d.devices ? d.devices.count : "—"}</dd>
          <dt>Dish pointing</dt><dd>${d.elevation !== null && d.elevation !== undefined ? `${fmtN(d.elevation, 0)}° up` : "—"}</dd>
          <dt>Speed right now</dt><dd>${fmtN(d.down_mbps, 1)} ↓ / ${fmtN(d.up_mbps, 1)} ↑ Mbps</dd>
          <dt>GPS satellites</dt><dd>${fmtN(d.gps_sats)}</dd>
          <dt>On for</dt><dd>${dur(d.uptime_s)}</dd>
          <dt>Dish location</dt><dd>${d.location ? "Shared" : d.location_supported === false ? "Not shared by Starlink" : "—"}</dd>
          <dt>Firmware</dt><dd>${esc(d.software || "—")}</dd>
          <dt>Hardware</dt><dd>${esc(d.hardware || "—")}</dd>
        </dl>
        <button class="btn danger block" id="slRestart">${ic("power")} Restart Starlink</button>
      </section>`;

    v.querySelectorAll("[data-h]").forEach((b) => b.onclick = () => { state.stRange = Number(b.dataset.h); render(); });
    document.getElementById("slRestart").onclick = () => runCommand("restart_dish");
    document.getElementById("slSpeed").onclick = () => runSpeedTest();
    document.getElementById("planBtn").onclick = () => planSheet();
    bindSettings(v);
    loadStarlinkExtras();

    try {
      const [h, u] = await Promise.all([api(`/api/history?hours=${state.stRange}`), api("/api/usage?days=30")]);
      if (state.route !== "starlink") return;
      const rows = h.rows.filter((r) => r.net === "starlink");
      const pts = (k) => rows.map((r) => ({ x: r.ts, y: r[k] }));
      const accent = cssVar("--accent"), beam = cssVar("--beam");
      document.getElementById("histNote").textContent = rows.length ? `${rows.length} check-ins while on Starlink. Gaps are times the car was asleep.` : "No Starlink data in this window yet. It fills in as you drive.";
      state.charts.push(new Chart(document.getElementById("cPing"), { type: "line", data: { datasets: [lineDs("Ping", pts("ping"), accent, true)] }, options: chartOpts("") }));
      state.charts.push(new Chart(document.getElementById("cThru"), { type: "line", data: { datasets: [lineDs("Down", pts("down"), beam, true), lineDs("Up", pts("up"), accent)] }, options: chartOpts("", { legend: true }) }));
      state.charts.push(new Chart(document.getElementById("cDrop"), { type: "line", data: { datasets: [lineDs("Dropped", pts("drop_pct"), accent, true), lineDs("Sky blocked", pts("obstructed"), beam)] }, options: chartOpts("", { legend: true }) }));
      const urows = u.rows;
      const todayRow = (state.ov && state.ov.today) || {};
      const month = urows.reduce((a, r) => a + (r.down_mb || 0) + (r.up_mb || 0), 0);
      document.getElementById("usageStats").innerHTML = `
        <div class="stat"><div class="k">Today</div><div class="v">${fmtN((todayRow.down_mb || 0) + (todayRow.up_mb || 0), 0, " MB")}</div></div>
        <div class="stat"><div class="k">30 days</div><div class="v">${fmtN(month / 1000, 1, " GB")}</div></div>
        <div class="stat"><div class="k">Footage uploads</div><div class="v">${fmtN(urows.reduce((a, r) => a + (r.clips_mb || 0), 0) / 1000, 1, " GB")}</div></div>`;
      const grid = cssVar("--line"), ink = cssVar("--muted");
      state.charts.push(new Chart(document.getElementById("cUsage"), {
        type: "bar",
        data: { labels: urows.map((r) => r.day.slice(5).replace("-", "/")), datasets: [
          { label: "Download", data: urows.map((r) => r.down_mb || 0), backgroundColor: beam, borderRadius: 4, stack: "s" },
          { label: "Upload", data: urows.map((r) => r.up_mb || 0), backgroundColor: accent, borderRadius: 4, stack: "s" }] },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: ink, boxWidth: 10, usePointStyle: true } }, tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${Math.round(c.parsed.y)} MB` } } },
          scales: { x: { stacked: true, grid: { display: false }, ticks: { color: ink, maxTicksLimit: 8 } }, y: { stacked: true, beginAtZero: true, grid: { color: grid }, ticks: { color: ink, maxTicksLimit: 5, callback: (x) => x + " MB" } } } },
      }));
    } catch (e) { /* section shows its empty note */ }
  }

  function planSheet() {
    const cur = S();
    sheet(`<h2>Monthly data limit</h2><div class="muted">If your Starlink plan has a data limit, put it here. You'll see how much is used, get a heads-up at 80%, and footage uploads can wait for home WiFi near the end.</div>
      <form id="planForm" class="steps">
        <div class="field"><label for="pGb">Plan size in GB (0 = no limit)</label><input class="input" id="pGb" type="number" inputmode="numeric" min="0" max="10000" value="${cur.plan_gb || 0}"></div>
        <div class="field"><label for="pDay">Day of the month it resets</label><input class="input" id="pDay" type="number" inputmode="numeric" min="1" max="28" value="${cur.plan_reset_day || 1}"></div>
        <button class="btn primary block" type="submit">Save</button>
      </form>`, (el, close) => {
      el.querySelector("#planForm").onsubmit = (e) => { e.preventDefault(); close(); saveSetting({ plan_gb: Number(el.querySelector("#pGb").value) || 0, plan_reset_day: Number(el.querySelector("#pDay").value) || 1 }, "Saved"); };
    });
  }
  function drawSky(sky) {
    const cv = document.getElementById("sky"), pill = document.getElementById("skyPill");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    ctx.clearRect(0, 0, cv.width, cv.height);
    if (!sky || !sky.data) { pill.textContent = "No picture yet"; document.getElementById("skyNote").textContent = "The dish builds this picture as it runs. It shows up here after the Pi has been on the Starlink for a few minutes."; return; }
    const raw = atob(sky.data), w = sky.w, h = sky.h, cell = cv.width / w;
    const clear = cssVar("--beam"), blocked = cssVar("--bad"), none = cssVar("--surface-2");
    let known = 0, good = 0;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const b = raw.charCodeAt(y * w + x);
      if (b === 255) { ctx.globalAlpha = 1; ctx.fillStyle = none; }
      else { known++; const val = b / 254; if (val >= 0.5) { good++; ctx.fillStyle = clear; ctx.globalAlpha = 0.35 + 0.65 * val; } else { ctx.fillStyle = blocked; ctx.globalAlpha = 1 - val; } }
      ctx.fillRect(x * cell, y * cell, cell + 0.5, cell + 0.5);
    }
    ctx.globalAlpha = 1;
    const pct = known ? Math.round((100 * good) / known) : null;
    pill.textContent = pct === null ? "Still scanning" : `${pct}% clear`;
    pill.className = "pill " + (pct === null ? "" : pct >= 90 ? "ok" : pct >= 75 ? "warn" : "bad");
    cv.title = `Updated ${ago(sky.at)}`;
  }
  async function loadStarlinkExtras() {
    const grid = cssVar("--line"), ink = cssVar("--muted"), accent = cssVar("--accent"), beam = cssVar("--beam");
    api("/api/skymap").then((r) => { if (state.route === "starlink") drawSky(r.sky); }).catch(() => {});
    try {
      const [sp, out] = await Promise.all([api("/api/speedtests?days=30"), api("/api/outages?days=14")]);
      if (state.route !== "starlink") return;
      const tests = sp.rows.slice().reverse();
      const tip = { callbacks: { title: (items) => items.length ? new Date(items[0].parsed.x * 1000).toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "", label: (c) => `${c.dataset.label}: ${Math.round(c.parsed.y)} Mbps` } };
      if (tests.length > 1 && document.getElementById("cSpeed")) {
        const ds = (label, key, color) => ({ label, data: tests.map((t) => ({ x: t.at, y: t[key] })), borderColor: color, backgroundColor: color, pointRadius: 3, pointHoverRadius: 6, borderWidth: 2, tension: .25 });
        state.charts.push(new Chart(document.getElementById("cSpeed"), { type: "line", data: { datasets: [ds("Download", "down", beam), ds("Upload", "up", accent)] },
          options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false }, plugins: { legend: { labels: { color: ink, boxWidth: 10, usePointStyle: true } }, tooltip: tip },
            scales: { x: { type: "linear", grid: { display: false }, ticks: { color: ink, maxTicksLimit: 5, callback: (v) => new Date(v * 1000).toLocaleDateString([], { month: "numeric", day: "numeric" }) } }, y: { beginAtZero: true, grid: { color: grid }, ticks: { color: ink, maxTicksLimit: 4 }, title: { display: true, text: "Mbps", color: ink } } } } }));
      } else if (document.getElementById("cSpeed")) document.getElementById("cSpeed").parentElement.hidden = true;
      const days = out.per_day.filter((r) => (r.starlink_s || 0) > 120);
      if (days.length && document.getElementById("cGood")) {
        state.charts.push(new Chart(document.getElementById("cGood"), { type: "bar",
          data: { labels: days.map((r) => r.day.slice(5).replace("-", "/")), datasets: [{ label: "Good signal", data: days.map((r) => Math.round((1000 * (r.good_s || 0)) / r.starlink_s) / 10), backgroundColor: accent, borderRadius: 4, maxBarThickness: 22 }] },
          options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${c.parsed.y}% good · on Starlink ${durShort(days[c.dataIndex].starlink_s)}` } } },
            scales: { x: { grid: { display: false }, ticks: { color: ink, maxTicksLimit: 7 } }, y: { min: Math.max(0, Math.floor(Math.min(...days.map((r) => (100 * (r.good_s || 0)) / r.starlink_s)) / 10) * 10 - 10), max: 100, grid: { color: grid }, ticks: { color: ink, maxTicksLimit: 4, callback: (x) => x + "%" } } } } }));
      } else if (document.getElementById("cGood")) document.getElementById("cGood").parentElement.hidden = true;
      const list = document.getElementById("dropList");
      if (list) list.innerHTML = out.rows.length ? `<ul class="list">${out.rows.slice(0, 8).map((o) => `<li class="item"><span class="dot problem"></span><div class="body"><div class="t">${esc(durShort(o.end - o.start))} without service</div><div class="m">${esc(o.cause)}</div></div><span class="when">${esc(friendlyDate(new Date(o.start * 1000)))}</span></li>`).join("")}</ul>${out.rows.length > 8 ? `<a class="small" href="#activity">See all ${out.rows.length} in Activity</a>` : ""}` : `<div class="empty">${ic("check")}<div>No drops in the last 14 days.</div></div>`;
    } catch { /* cards keep their empty state */ }
  }

  // ---------- ACTIVITY (everything that happened, newest first) ----------
  async function renderActivity(v) {
    const f = state.actFilter || "all";
    const chips = [["all", "All"], ["clip", "Clips"], ["problem", "Problems"], ["drop", "Drops"], ["awake", "Car awake"], ["info", "Updates"]];
    v.innerHTML = `<div class="chips scroll">${chips.map(([k, l]) => `<button class="chip ${f === k ? "on" : ""}" data-f="${k}">${l}</button>`).join("")}</div>
      <section class="card"><div id="actList"><div class="skeleton"></div></div></section>`;
    v.querySelectorAll("[data-f]").forEach((b) => b.onclick = () => { state.actFilter = b.dataset.f; render(); });
    try {
      const r = await api("/api/timeline?days=14");
      if (state.route !== "activity") return;
      let items = r.alerts.map((a) => ({ at: a.at, kind: ["clip", "problem"].includes(a.category) ? a.category : "info", dot: a.category, t: a.title, m: a.message }))
        .concat(r.outages.map((o) => ({ at: o.start, kind: "drop", dot: "problem", t: `Starlink dropped for ${durShort(o.end - o.start)}`, m: o.cause })))
        .concat(r.sessions.map((x) => ({ at: x.start, kind: "awake", dot: "info", t: `Car awake for ${durShort(x.end - x.start)}`, m: x.net === "starlink" ? "On the Starlink" : "On WiFi" })))
        .concat(r.speedtests.map((x) => ({ at: x.at, kind: "info", dot: "info", t: `Speed test: ${Math.round(x.down)} down / ${Math.round(x.up)} up`, m: `${Math.round(x.ping)} ms ping${x.auto ? " · automatic" : ""}` })));
      if (f !== "all") items = items.filter((i) => i.kind === f);
      items.sort((a, b) => b.at - a.at);
      const el = document.getElementById("actList");
      if (!items.length) { el.innerHTML = `<div class="empty">${ic("list")}<div>Nothing here in the last 14 days.</div></div>`; return; }
      let html = "", lastDay = "";
      for (const i of items.slice(0, 250)) {
        const d = new Date(i.at * 1000), day = d.toDateString();
        if (day !== lastDay) { if (lastDay) html += "</ul>"; lastDay = day; const today = new Date().toDateString() === day; html += `<h3 class="day">${today ? "Today" : esc(d.toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" }))}</h3><ul class="list">`; }
        html += `<li class="item"><span class="dot ${esc(i.dot)}"></span><div class="body"><div class="t">${esc(i.t)}</div><div class="m">${esc(i.m || "")}</div></div><span class="when">${esc(d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }))}</span></li>`;
      }
      el.innerHTML = html + "</ul>";
    } catch (e) { const el = document.getElementById("actList"); if (el) el.innerHTML = `<div class="muted">Couldn't load. Pull down or tap refresh.</div>`; }
  }

  // ---------- DRIVE MODE (big, glanceable, for a phone mount or the car's browser) ----------
  let wakeLock = null;
  function releaseWake() { try { wakeLock && wakeLock.release(); } catch {} wakeLock = null; }
  function renderDrive(v) {
    const D = derive();
    const d = D.d;
    const q = qualityBars(d, D.fresh && D.onStarlink);
    const word = !D.fresh ? "Car asleep" : !D.onStarlink ? "On " + (D.pi.wifi_ssid || "WiFi") : D.outage ? "No service" : ["No signal", "Searching", "Weak", "Good", "Great"][q];
    const lvl = !D.fresh ? "" : D.outage || q <= 1 ? "bad" : q === 2 ? "warn" : "ok";
    if (!wakeLock && navigator.wakeLock) navigator.wakeLock.request("screen").then((l) => { wakeLock = l; }).catch(() => {});
    v.innerHTML = `<div class="drive ${lvl}">
      <div class="row between"><span class="pill ${lvl} ${D.fresh ? "live" : ""}">${D.fresh ? "Live" : "Offline"} · ${esc(ago(state.ov && state.ov.status_at))}</span><a class="icon-btn" href="#home" aria-label="Leave drive mode">${ic("x")}</a></div>
      <div class="d-main"><div class="d-bars">${barsHtml(q)}</div><div class="d-word">${esc(word)}</div>
        <div class="d-sub">${D.outage ? esc(`${durShort(D.outage.seconds)} · ${D.outage.cause}`) : D.fresh && D.onStarlink ? `<span class="num">${fmtN(d.ping_ms, 0)}</span> ms${D.motion && D.motion.driving ? ` · <span class="num">${fmtN(D.motion.speed_mph, 0)}</span> mph` : ""}` : ""}</div></div>
      <div class="caps big">${worksNow(D).map(([t, l]) => `<span class="cap ${l}">${ic(l === "ok" ? "check" : "alert")}${esc(t)}</span>`).join("")}</div>
      <div class="d-grid">
        <div class="stat"><div class="k">Dashcam</div><div class="v">${!D.fresh ? "—" : D.carOk ? "Recording" : "Not connected"}</div></div>
        <div class="stat"><div class="k">Speed in use</div><div class="v">${D.fresh && D.onStarlink ? `${fmtN(d.down_mbps, 1)} ↓ ${fmtN(d.up_mbps, 1)} ↑` : "—"}</div></div>
        <div class="stat"><div class="k">Sky blocked</div><div class="v">${D.fresh && D.onStarlink ? fmtN(d.obstructed_pct, 1, "%") : "—"}</div></div>
        <div class="stat"><div class="k">Pi</div><div class="v">${D.fresh ? fmtN(D.pi.cpu_temp_c, 0, "°C") : "—"}</div></div>
      </div>
      <button class="btn primary d-save" id="dSave">${ic("save")} Save the last 10 minutes</button>
    </div>`;
    document.getElementById("dSave").onclick = () => runCommand("upload_recent", { minutes: 10 });
  }

  // ---------- MAP ----------
  async function renderMap(v) {
    const D = derive();
    const ov = state.ov || {};
    const L0 = ov.last_location;
    const loc = L0 && L0.lat !== null && L0.lat !== undefined ? { lat: L0.lat, lon: L0.lon } : null;
    const locAt = L0 && L0.ts;
    const gps = (D.s && D.s.gps) || {};
    const hasGps = !!gps.device;
    v.innerHTML = `
      <div class="row between">
        <div class="chips">${[[1, "Today"], [7, "Week"], [30, "Month"], [365, "Year"]].map(([d, l]) => `<button class="chip ${state.mapDays === d ? "on" : ""}" data-d="${d}">${l}</button>`).join("")}</div>
        <button class="chip ${state.mapProblems ? "on" : ""}" id="onlyBad">Problems only</button>
      </div>
      <div class="map-wrap"><div id="leaf"></div>
        <div class="map-over"><div class="glass" id="mapStats">Loading…</div>
          <button class="btn" id="findCar" style="min-height:40px;padding:6px 12px">${ic("car")} My car</button></div></div>
      <section class="card">
        <div class="row" style="gap:16px">
          <span class="row small" style="gap:6px"><span style="width:10px;height:10px;border-radius:50%;background:var(--ok)"></span>Good</span>
          <span class="row small" style="gap:6px"><span style="width:10px;height:10px;border-radius:50%;background:var(--warn)"></span>Weak</span>
          <span class="row small" style="gap:6px"><span style="width:10px;height:10px;border-radius:50%;background:var(--bad)"></span>Dropped</span>
        </div>
        <div class="row small" style="gap:16px"><span class="row" style="gap:6px"><span class="pin-dot sentry"></span>Sentry event</span><span class="row" style="gap:6px"><span class="pin-dot dashcam"></span>Saved clip</span></div>
        <div class="muted small">Dots are spots you've driven, colored by how the Starlink did there. Pins are your saved clips and Sentry events (from the car's own location data). ${loc ? `Car last seen ${esc(ago(locAt))}${L0.source === "gps" ? " (USB GPS)" : ""}.` : ""}</div>
        ${loc ? `<a class="btn block" href="https://maps.apple.com/?ll=${loc.lat},${loc.lon}&q=My%20Model%20Y" target="_blank" rel="noopener">${ic("ext")} Open car location in Maps</a>` : ""}
      </section>
      ${hasGps ? `<section class="card"><div class="card-head"><h2>USB GPS</h2><span class="pill ${gps.fix ? "ok" : "warn"}">${gps.fix ? "Locked on" : "Searching"}</span></div>
        <div class="muted small">${gps.fix ? `${fmtN(gps.sats)} satellites. Coverage dots and Find my car come from this.` : "Plugged in. It needs a view of the sky; the first lock can take a few minutes."}</div></section>` :
        `<section class="card"><div class="card-head"><h2>Want live location?</h2><span class="pill">Optional</span></div>
        <div class="banner">${ic("gps")}<div>Starlink stopped sharing the dish's location with devices on its WiFi in May 2026, so the coverage dots and Find my car need a small USB GPS on the Pi.</div></div>
        <div class="steps">
          <div class="step"><span class="n">1</span><span><div class="t">Get a USB GPS (about $15)</div><div class="d">Any “u-blox 7” or “VK-162” USB GPS stick works. Plus a USB-C to USB-A adapter (OTG).</div></span></div>
          <div class="step"><span class="n">2</span><span><div class="t">Plug it into the Pi's USB1</div><div class="d">The middle USB-C port. USB0 stays for the car cable.</div></span></div>
          <div class="step"><span class="n">3</span><span><div class="t">That's it</div><div class="d">The Pi finds it on its own. This card turns into a GPS status card, and dots start showing as you drive.</div></span></div>
        </div></section>`}`;

    v.querySelectorAll("[data-d]").forEach((b) => b.onclick = () => { state.mapDays = Number(b.dataset.d); render(); });
    document.getElementById("onlyBad").onclick = () => { state.mapProblems = !state.mapProblems; render(); };

    if (typeof L === "undefined") { document.getElementById("mapStats").textContent = "Map couldn't load. Check your connection."; return; }
    const map = L.map("leaf", { zoomControl: false, attributionControl: true, preferCanvas: true });
    state.map = map;
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, className: isDark() ? "tiles-dark" : "", attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' }).addTo(map);
    map.setView(loc ? [loc.lat, loc.lon] : [40.364, -111.738], loc ? 14 : 11);
    let carMarker = null;
    if (loc) {
      carMarker = L.marker([loc.lat, loc.lon], { icon: L.divIcon({ className: "", html: '<div class="car-pin"></div>', iconSize: [22, 22], iconAnchor: [11, 11] }) })
        .addTo(map).bindPopup(`<b>Your Model Y</b><br>Seen ${esc(ago(locAt))}`);
    }
    document.getElementById("findCar").onclick = () => {
      if (carMarker) { map.flyTo(carMarker.getLatLng(), 16, { duration: .8 }); carMarker.openPopup(); }
      else toast("No car location yet. A USB GPS on the Pi adds this (see below).");
    };
    try {
      const r = await api(`/api/coverage?days=${state.mapDays}`);
      if (state.map !== map) return;
      const col = { g: cssVar("--ok"), w: cssVar("--warn"), d: cssVar("--bad") };
      const order = { g: 0, w: 1, d: 2 };
      const pts = r.points.filter((p) => !state.mapProblems || p[3] !== "g").sort((a, b) => order[a[3]] - order[b[3]]);
      const bounds = [];
      pts.forEach((p) => {
        bounds.push([p[1], p[2]]);
        L.circleMarker([p[1], p[2]], { radius: p[3] === "g" ? 4 : 6, color: col[p[3]] || "#888", fillColor: col[p[3]] || "#888", fillOpacity: p[3] === "g" ? .55 : .9, weight: p[3] === "g" ? 0 : 2 })
          .addTo(map).bindPopup(`<b>${p[3] === "g" ? "Good" : p[3] === "w" ? "Weak" : "Dropped"}</b><br>${new Date(p[0] * 1000).toLocaleString([], { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}${p[4] ? `<br>Ping ${Math.round(p[4])} ms` : ""}`);
      });
      const all = r.points.length;
      const good = r.points.filter((p) => p[3] === "g").length;
      document.getElementById("mapStats").innerHTML = all ? `<b class="num">${all}</b> spots · <b class="num">${Math.round((100 * good) / all)}%</b> good` : "No drives logged yet";
      if (bounds.length && (state.focusCar !== true || !carMarker)) map.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
      if (state.focusCar && carMarker) { map.setView(carMarker.getLatLng(), 16); carMarker.openPopup(); }
      state.focusCar = false;
      // Clip pins (Sentry / saved clips) from the car's own event location
      api(`/api/clip-pins?days=${Math.max(state.mapDays, 30)}`).then((cp) => {
        if (state.map !== map || !cp.pins.length) return;
        const pinBounds = [];
        cp.pins.forEach((c) => {
          pinBounds.push([c.lat, c.lon]);
          const d = folderDate(c.folder);
          L.marker([c.lat, c.lon], { icon: L.divIcon({ className: "", html: `<div class="pin-dot ${c.kind === "sentry" ? "sentry" : "dashcam"}"></div>`, iconSize: [16, 16], iconAnchor: [8, 8] }) })
            .addTo(map).bindPopup(`<b>${esc(reasonText(c))}</b><br>${esc(friendlyDate(d) || ago(c.uploaded_at))}${c.city ? " · " + esc(c.city) : ""}<br><a href="${esc(c.drive_url || DRIVE[c.kind] || DRIVE.root)}" target="_blank" rel="noopener">Open in Drive</a>`);
        });
        if (!bounds.length && !carMarker && pinBounds.length) map.fitBounds(pinBounds, { padding: [30, 30], maxZoom: 15 });
      }).catch(() => {});
    } catch { document.getElementById("mapStats").textContent = "Couldn't load the map data."; }
  }

  // ---------- PI ----------
  async function renderPi(v) {
    const D = derive();
    const pi = D.pi, cam = D.cam;
    const svc = pi.services || {};
    const t = pi.cpu_temp_c;
    v.className = "two";
    v.innerHTML = `
      <section class="card wide">
        <div class="card-head"><h2>Orange Pi in the glovebox</h2><span class="pill ${!D.fresh ? "" : t >= 80 ? "bad" : t >= 70 ? "warn" : "ok"} ${D.fresh ? "live" : ""}">${!D.fresh ? "Off / asleep" : t >= 80 ? "Running hot" : "Running"}</span></div>
        <div class="gauges">
          ${gauge(D.fresh ? t : null, 100, "Temperature", "°C", true, 70, 80)}
          ${gauge(D.fresh ? (pi.load1 || 0) * 25 : null, 100, "Busy", "%", true, 60, 85)}
          ${gauge(D.fresh ? pi.mem_used_pct : null, 100, "Memory", "%", true, 75, 90)}
        </div>
        <dl class="kv">
          <dt>WiFi</dt><dd>${esc(pi.wifi_ssid || "None")} ${pi.wifi_signal ? `(${pi.wifi_signal}%)` : ""}</dd>
          <dt>Internet</dt><dd>${D.fresh ? (pi.internet ? "Yes" : "No") : "—"}</dd>
          <dt>On for</dt><dd>${dur(pi.uptime_s)}</dd>
          <dt>SD card free</dt><dd>${fmtN(pi.sd_free_gb, 1, " GB")}</dd>
          <dt>Tailscale</dt><dd>${esc(pi.tailscale_ip || "—")}</dd>
          <dt>Version</dt><dd>${pi.version ? "v" + esc(pi.version) : state.ov && state.ov.versions && state.ov.versions.pi ? "v" + esc(state.ov.versions.pi) : "—"} ${pi.code_version ? `<span class="muted">(${esc(pi.code_version)})</span>` : ""}</dd>
          <dt>Time zone</dt><dd>${esc(pi.timezone || "—")}</dd>
          <dt>Last check-in</dt><dd>${esc(ago(state.ov && state.ov.status_at))}</dd>
        </dl>
      </section>

      ${softwareCard()}

      <section class="card">
        <div class="card-head"><h2>Temperature</h2><div class="chips">${[[24, "24h"], [168, "7d"]].map(([h, l]) => `<button class="chip ${state.stRange === h ? "on" : ""}" data-h="${h}">${l}</button>`).join("")}</div></div>
        <div class="chart-box"><canvas id="cTemp"></canvas></div>
        <div class="muted small">Over 80°C sends you an alert. A small heatsink keeps it cooler in summer.</div>
      </section>

      <section class="card">
        <div class="card-head"><h2>What's running</h2></div>
        <ul class="list">
          ${[["car-atlas-teslacam", "Dashcam drive", cam.gadget === "attached" ? (D.carOk ? "Car is recording to it" : "Offered, car not connected yet") : cam.gadget === "unsupported" ? "Not supported on this Pi" : cam.gadget || "—"],
             ["car-atlas-uploader", "Clip uploader", cam.waiting_for ? "Waiting for " + cam.waiting_for : cam.uploading ? "Uploading" : "Watching for clips"],
             ["car-atlas-monitor", "Starlink + health monitor", "Checking every 15 s"],
             ["tailscaled", "Tailscale (remote access)", pi.tailscale_ip || ""]].map(([k, name, sub]) => {
            const ok = svc[k] === "active";
            return `<li class="item"><span class="dot" style="background:${!D.s ? "var(--line)" : ok ? "var(--ok)" : "var(--bad)"}"></span>
              <div class="body"><div class="t">${esc(name)}</div><div class="m">${esc(sub)}</div></div>
              <span class="when">${D.s ? esc(svc[k] || "unknown") : ""}</span></li>`;
          }).join("")}
        </ul>
      </section>

      <section class="card">
        <div class="card-head"><h2>Check on the Pi</h2></div>
        <div class="muted small">Runs on the Pi and shows you the report right here. No laptop needed.</div>
        <div class="row">
          <button class="btn" style="flex:1" data-diag="doctor">${ic("pulse")} Health check</button>
          <button class="btn" style="flex:1" data-diag="usb_debug">${ic("usb")} USB check</button>
        </div>
        <div class="row">
          <button class="btn" style="flex:1" data-diag="logs">${ic("list")} Recent logs</button>
          <button class="btn" style="flex:1" data-diag="sysinfo">${ic("cpu")} What's it doing</button>
        </div>
        ${toggleRow("heat_protect", "Protect the Pi from heat", "Clip uploads pause above 84°C and pick back up once it cools.", S().heat_protect)}
        ${cam.hot_hold ? `<div class="banner warn">${ic("therm")}<div>Uploads are paused right now so the Pi can cool down.</div></div>` : ""}
      </section>

      <section class="card">
        <div class="card-head"><h2>Remote control</h2></div>
        <div class="muted small">These go to the Pi the next time it checks in (every ~30 s while the car is awake).</div>
        <div class="row">
          <button class="btn" style="flex:1" data-cmd="update_now">${ic("save")} Check for updates</button>
          <button class="btn" style="flex:1" data-cmd="test_alert">${ic("bell")} Test alert</button>
        </div>
        <div class="row">
          <button class="btn" style="flex:1" data-cmd="restart_services">${ic("refresh")} Restart services</button>
          <button class="btn danger" style="flex:1" data-cmd="reboot_pi">${ic("power")} Restart Pi</button>
        </div>
      </section>

      <section class="card">
        <div class="card-head"><h2>Sent to the Pi</h2></div>
        ${commandsList((state.ov && state.ov.commands) || [], state.ov && state.ov.command_labels)}
      </section>`;

    v.querySelectorAll("[data-cmd]").forEach((b) => b.onclick = () => runCommand(b.dataset.cmd));
    v.querySelectorAll("[data-h]").forEach((b) => b.onclick = () => { state.stRange = Number(b.dataset.h); render(); });
    v.querySelectorAll("[data-diag]").forEach((b) => b.onclick = () => runDiagnostic(b.dataset.diag));
    v.querySelectorAll("[data-out]").forEach((b) => b.onclick = () => openCommandOutput(b.dataset.out));
    bindSettings(v);
    bindSoftware(v);
    try {
      const h = await api(`/api/history?hours=${state.stRange >= 168 ? 168 : 24}`);
      if (state.route !== "pi") return;
      const warn = cssVar("--warn");
      state.charts.push(new Chart(document.getElementById("cTemp"), {
        type: "line", data: { datasets: [lineDs("Temp", h.rows.map((r) => ({ x: r.ts, y: r.temp })), warn, true)] },
        options: chartOpts("", { y: { beginAtZero: false, suggestedMin: 30, suggestedMax: 85 } }),
      }));
    } catch {}
  }

  // ---------- versions / software ----------
  function softwareCard() {
    const V = verInfo();
    const u = V.upd || {};
    const lastCheck = u.checked_at ? `${{ "up-to-date": "Up to date", updated: `Updated v${u.from} → v${u.to}`, offline: "Couldn't reach GitHub" }[u.result] || u.result} · ${ago(u.checked_at)}` : "—";
    return `<section class="card wide" id="swCard">
      <div class="card-head"><h2>Software</h2><span class="pill ${V.level}">${esc(V.text)}</span></div>
      <div class="vers">
        <div class="vbox ${V.behind ? "warn" : V.level === "ok" ? "ok" : ""}"><div class="k">Pi is running</div><div class="v num">${V.pi ? "v" + esc(V.pi) : "—"}</div><div class="s">${V.pi_reported_at ? "reported " + esc(ago(V.pi_reported_at)) : "not reported yet"}</div></div>
        <div class="varrow" aria-hidden="true">${V.behind ? "→" : V.level === "ok" ? "=" : ""}</div>
        <div class="vbox"><div class="k">Should be on</div><div class="v num">${V.latest ? "v" + esc(V.latest) : "—"}</div><div class="s">${V.latest_checked_at ? "newest release · checked " + esc(ago(V.latest_checked_at)) : "newest release"}</div></div>
      </div>
      ${V.behind ? `<div class="banner warn">${ic("save")}<div>${esc(V.note)}</div></div>` : ""}
      <dl class="kv">
        <dt>Pi code</dt><dd>${esc(V.pi_sha || "—")}</dd>
        <dt>Pi's last update check</dt><dd>${esc(lastCheck)}</dd>
        <dt>This app</dt><dd>v${esc(APP_VERSION)}${V.app && V.app !== APP_VERSION ? ` (server v${esc(V.app)})` : ""}</dd>
      </dl>
      <div class="row">
        <button class="btn ${V.behind ? "primary" : ""}" style="flex:1" data-cmd="update_now">${ic("refresh")} ${V.behind ? "Update now" : "Check for updates"}</button>
        <button class="btn" style="flex:1" data-whatsnew>${ic("star")} What's new</button>
      </div>
      <div class="muted small">The Pi checks for updates right after it turns on and every 30 minutes. Updates never interrupt the dashcam.</div>
    </section>`;
  }
  function bindSoftware(root) {
    root.querySelectorAll("[data-whatsnew]").forEach((b) => b.onclick = whatsNew);
  }
  function mdLite(md) {
    // Tiny markdown: "## heading", "- bullet" (with wrapped lines), `code`
    const out = [];
    let li = null;
    const flush = () => { if (li !== null) { out.push(`<li>${li}</li>`); li = null; } };
    const inline = (t) => esc(t).replace(/`([^`]+)`/g, "<code>$1</code>");
    let inList = false;
    for (const raw of String(md || "").split("\n")) {
      const line = raw.trimEnd();
      if (/^#\s/.test(line)) continue;
      if (/^##\s/.test(line)) { flush(); if (inList) { out.push("</ul>"); inList = false; } out.push(`<h3>${inline(line.replace(/^##\s*/, ""))}</h3>`); continue; }
      if (/^\s*-\s/.test(line)) { flush(); if (!inList) { out.push("<ul>"); inList = true; } li = inline(line.replace(/^\s*-\s*/, "")); continue; }
      if (line.trim() && li !== null) { li += " " + inline(line.trim()); continue; }
      flush();
    }
    flush(); if (inList) out.push("</ul>");
    return out.join("");
  }
  async function whatsNew() {
    const close = sheet(`<h2>What's new</h2><div class="changelog"><div class="skeleton" style="min-height:120px"></div></div>
      <button class="btn block" data-close>Close</button>`, (el, c) => { el.querySelector("[data-close]").onclick = c; });
    try {
      const r = await api("/api/changelog");
      const box = document.querySelector(".sheet .changelog");
      if (box) box.innerHTML = r.text ? mdLite(r.text) : `<div class="muted">Couldn't load the notes right now.</div>`;
    } catch { const box = document.querySelector(".sheet .changelog"); if (box) box.innerHTML = `<div class="muted">Couldn't load the notes right now.</div>`; }
    return close;
  }
  // When the server is running a newer app than this page, offer a one-tap reload.
  function checkAppUpdate() {
    const sv = state.ov && state.ov.app_version;
    if (!sv || cmpVer(sv, APP_VERSION) <= 0 || state.appUpdateShown) return;
    state.appUpdateShown = true;
    const bar = document.createElement("button");
    bar.className = "update-bar";
    bar.innerHTML = `${ic("star")}<span>App v${esc(sv)} is ready · tap to update</span>`;
    bar.onclick = async () => {
      bar.disabled = true;
      try { const reg = await navigator.serviceWorker?.getRegistration(); await reg?.update(); } catch {}
      location.reload();
    };
    document.body.append(bar);
  }

  // ---------- SETTINGS ----------
  async function pushStatus() {
    try {
      if (!("serviceWorker" in navigator) || !("PushManager" in window)) return { supported: false };
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.getSubscription();
      if (!sub) return { supported: true, on: false };
      const r = await api("/api/push/status", { method: "POST", body: { endpoint: sub.endpoint } });
      return { supported: true, on: r.subscribed, prefs: r.prefs, devices: r.devices, sub };
    } catch { return { supported: false }; }
  }
  function urlB64ToUint8Array(b64) {
    const pad = "=".repeat((4 - (b64.length % 4)) % 4);
    const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(raw, (c) => c.charCodeAt(0));
  }
  async function enablePush() {
    try {
      const perm = await Notification.requestPermission();
      if (perm !== "granted") { toast("Notifications are blocked. Allow them in iPhone Settings → Notifications → Car Atlas."); return; }
      const reg = await navigator.serviceWorker.ready;
      const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlB64ToUint8Array(state.me.vapid_public) });
      await api("/api/push/subscribe", { method: "POST", body: { ...sub.toJSON(), label: isIOS() ? "iPhone" : "Browser" } });
      state.pushOn = true;
      toast("Notifications on!");
      render();
    } catch (e) { toast("Couldn't turn them on: " + (e.message || e)); }
  }

  async function renderSettings(v) {
    const ov = state.ov || {};
    const D = derive();
    v.className = "two";
    v.innerHTML = `
      <section class="card wide">
        <div class="card-head"><h2>Connect the Pi</h2><span class="pill ${ov.paired ? "ok" : ""}">${ov.paired ? "Connected" : "Not connected"}</span></div>
        ${ov.paired ? `<div class="muted small">Linked ${esc(ago(ov.paired_at))}. Last check-in ${esc(ago(ov.status_at))}. Making a new code links the Pi again (only one Pi at a time).</div>` :
          `<div class="muted small">On your Mac, log into the Pi (<span class="num">ssh orangepi@100.87.46.66</span>), then paste the command below. It installs everything and links the Pi to this app.</div>`}
        <button class="btn ${ov.paired ? "" : "primary"} block" id="mkCode">${ic("lock")} ${ov.paired ? "Make a new connect code" : "Make my connect code"}</button>
        <div id="codeOut"></div>
      </section>

      <section class="card">
        <div class="card-head"><h2>Notifications</h2><span class="pill" id="pushPill">Checking…</span></div>
        <div id="pushBody"><div class="skeleton" style="min-height:60px"></div></div>
      </section>

      <section class="card">
        <div class="card-head"><h2>Google Drive</h2><span class="pill ${D.s && D.s.drive_setup ? "ok" : ""}">${D.s ? (D.s.drive_setup ? "Connected" : "Not set up") : "—"}</span></div>
        ${D.s && D.s.drive_setup ? `<div class="muted small">Clips upload to Tesla Footage in your Drive.</div>` :
          `<div class="steps">
            <div class="step"><span class="n">1</span><span><div class="t">On the Pi</div><div class="code">sudo car-atlas drive-setup</div></span></div>
            <div class="step"><span class="n">2</span><span><div class="t">It tells you what to run on your Mac</div><div class="d">A browser opens. Sign in with your Google account and click Allow, then paste the result back into the Pi.</div></span></div>
          </div>`}
        <div class="row"><a class="btn" style="flex:1" href="${DRIVE.root}" target="_blank" rel="noopener">${ic("drive")} Open Tesla Footage</a></div>
      </section>

      <section class="card">
        <div class="card-head"><h2>Add to Home Screen</h2><span class="pill ${standalone() ? "ok" : ""}">${standalone() ? "Installed" : "In Safari"}</span></div>
        <div class="muted small">${standalone() ? "You're using the app version. Nice." : "In Safari, tap the Share button, then “Add to Home Screen”. You need this for notifications on iPhone."}</div>
      </section>

      <section class="card">
        <div class="card-head"><h2>Password</h2></div>
        <form id="pwForm" class="steps">
          <div class="field"><label for="pwCur">Current password</label><input class="input" id="pwCur" type="password" autocomplete="current-password" required></div>
          <div class="field"><label for="pwNew">New password</label><input class="input" id="pwNew" type="password" autocomplete="new-password" minlength="8" required></div>
          <button class="btn primary" type="submit">Change password</button>
        </form>
        <div class="muted small">Your wife can use the same password on her phone.</div>
      </section>

      <section class="card">
        <div class="card-head"><h2>Share the car WiFi</h2><span class="pill ${ov.wifi_set ? "ok" : ""}">${ov.wifi_set ? "Ready" : "Not set"}</span></div>
        <div class="muted small">A code passengers scan with their camera to join the Starlink. No typing the password.</div>
        <button class="btn block" id="wifiBtn">${ic("qr")} ${ov.wifi_set ? "Show the code" : "Set it up"}</button>
      </section>

      <section class="card">
        <div class="card-head"><h2>Siri Shortcuts</h2><span class="pill ${ov.shortcut_set ? "ok" : ""}">${ov.shortcut_set ? "Link made" : "Off"}</span></div>
        <div class="muted small">Say “Hey Siri, car status” or “save my dashcam” without opening the app. Make a private link, then add it to the Shortcuts app.</div>
        <button class="btn block" id="scBtn">${ic("mic")} ${ov.shortcut_set ? "Make a new link (old one stops working)" : "Make my private link"}</button>
        <div id="scOut"></div>
      </section>

      <section class="card">
        <div class="card-head"><h2>About</h2>${(() => { const V = verInfo(); return `<span class="pill ${V.level}">${esc(V.behind ? "Pi update waiting" : V.level === "ok" ? "All up to date" : V.text)}</span>`; })()}</div>
        <dl class="kv">
          <dt>App</dt><dd>v${esc(APP_VERSION)}</dd>
          <dt>Pi</dt><dd>${(() => { const V = verInfo(); return V.pi ? "v" + esc(V.pi) : "—"; })()}</dd>
          <dt>Newest release</dt><dd>${(() => { const V = verInfo(); return V.latest ? "v" + esc(V.latest) : "—"; })()}</dd>
        </dl>
        <div class="row"><button class="btn" style="flex:1" data-whatsnew>${ic("star")} What's new</button><a class="btn" style="flex:1" href="#pi">${ic("cpu")} Pi software</a></div>
      </section>

      <section class="card">
        <div class="card-head"><h2>Account</h2></div>
        <div class="row">
          <button class="btn" style="flex:1" id="logout">${ic("out")} Sign out</button>
          <button class="btn danger" style="flex:1" id="logoutAll">Sign out everywhere</button>
        </div>
      </section>`;

    document.getElementById("mkCode").onclick = async () => {
      try {
        const r = await api("/api/pairing-code", { method: "POST", body: {} });
        const install = `curl -fsSL ${INSTALL_URL} | sudo bash -s -- ${r.code}`;
        const pairOnly = `sudo car-atlas pair ${r.code}`;
        document.getElementById("codeOut").innerHTML = `
          <div class="muted small">Your code <b class="num">${esc(r.code)}</b> works once and expires in 30 minutes.</div>
          <div class="t" style="font-weight:600">First time? Paste this on the Pi:</div>
          <div class="code" id="c1">${esc(install)}</div>
          <button class="btn block" id="cp1">${ic("copy")} Copy install command</button>
          <div class="t" style="font-weight:600">Already installed? Use this instead:</div>
          <div class="code" id="c2">${esc(pairOnly)}</div>
          <button class="btn block" id="cp2">${ic("copy")} Copy connect command</button>`;
        document.getElementById("cp1").onclick = () => copyText(install);
        document.getElementById("cp2").onclick = () => copyText(pairOnly);
      } catch (e) { if (e.message !== "auth") toast(e.message); }
    };
    document.getElementById("pwForm").onsubmit = async (e) => {
      e.preventDefault();
      try {
        await api("/api/settings/password", { method: "POST", body: { current: document.getElementById("pwCur").value, next: document.getElementById("pwNew").value } });
        toast("Password changed");
        e.target.reset();
      } catch (er) { if (er.message !== "auth") toast(er.message); }
    };
    bindSoftware(v);
    document.getElementById("wifiBtn").onclick = () => wifiSheet();
    document.getElementById("scBtn").onclick = async () => {
      if (ov.shortcut_set && !(await confirmSheet({ title: "Make a new link?", body: "Any shortcut using the old link stops working until you paste in the new one.", yes: "Make a new one" }))) return;
      try {
        const r = await api("/api/settings/shortcut-key", { method: "POST", body: {} });
        if (state.ov) state.ov.shortcut_set = true;
        const links = [["Car status (Siri reads it out)", `${r.base}/status`], ["Save the last 10 minutes of dashcam", `${r.base}/save?minutes=10`], ["Run a speed test", `${r.base}/speedtest`]];
        document.getElementById("scOut").innerHTML = `<div class="muted small">These links only show once. Copy the ones you want now.</div>
          ${links.map(([t, u], i) => `<div class="t" style="font-weight:600">${t}</div><div class="code">${esc(u)}</div><button class="btn block" data-cp="${i}">${ic("copy")} Copy link</button>`).join("")}
          <div class="steps">
            <div class="step"><span class="n">1</span><span><div class="t">Open the Shortcuts app → tap +</div></span></div>
            <div class="step"><span class="n">2</span><span><div class="t">Add the action “Get Contents of URL”</div><div class="d">Paste one of the links into it.</div></span></div>
            <div class="step"><span class="n">3</span><span><div class="t">Add the action “Speak Text”</div><div class="d">It reads the Pi's answer out loud.</div></span></div>
            <div class="step"><span class="n">4</span><span><div class="t">Name it what you want to say</div><div class="d">Like “Car status”. Then it's “Hey Siri, car status”.</div></span></div>
          </div>`;
        document.querySelectorAll("#scOut [data-cp]").forEach((b) => b.onclick = () => copyText(links[Number(b.dataset.cp)][1]));
      } catch (e) { if (e.message !== "auth") toast(e.message); }
    };
    document.getElementById("logout").onclick = async () => { await api("/api/logout", { method: "POST", body: {} }).catch(() => {}); state.authed = false; renderLogin(); };
    document.getElementById("logoutAll").onclick = async () => {
      if (!(await confirmSheet({ title: "Sign out everywhere?", body: "Every phone and browser will need the password again, including yours.", yes: "Sign out all", danger: true }))) return;
      await api("/api/sessions/logout-all", { method: "POST", body: {} }).catch(() => {});
      state.authed = false; renderLogin();
    };

    const ps = await pushStatus();
    state.pushOn = !!ps.on;
    const pill = document.getElementById("pushPill"), body = document.getElementById("pushBody");
    if (!pill) return;
    if (!ps.supported) {
      pill.textContent = "Not available here"; pill.className = "pill";
      body.innerHTML = `<div class="muted small">${isIOS() && !standalone() ? "On iPhone, add Car Atlas to your Home Screen first (Share → Add to Home Screen), then open it from there and come back here." : "This browser doesn't support notifications."}</div>`;
      return;
    }
    if (!ps.on) {
      pill.textContent = "Off"; pill.className = "pill";
      body.innerHTML = `<div class="muted small">Get a ping when a clip lands in Drive, the Pi runs hot, or the dashcam needs you.</div>
        <button class="btn primary block" id="pushOn">${ic("bell")} Turn on notifications</button>`;
      document.getElementById("pushOn").onclick = enablePush;
      return;
    }
    pill.textContent = "On"; pill.className = "pill ok";
    const prefs = ps.prefs || {};
    const rowT = (k, t, d) => `<label class="toggle"><span><div style="font-weight:600">${t}</div><div class="muted small">${d}</div></span>
      <span class="switch"><input type="checkbox" data-pref="${k}" ${prefs[k] !== false ? "checked" : ""}><span></span></span></label>`;
    const quiet = prefs.quiet || { on: false, from: 22, to: 7 };
    const hourOpts = (sel) => Array.from({ length: 24 }, (_, h) => `<option value="${h}" ${h === Number(sel) ? "selected" : ""}>${h === 0 ? "12 AM" : h < 12 ? h + " AM" : h === 12 ? "12 PM" : h - 12 + " PM"}</option>`).join("");
    body.innerHTML = `<div>${rowT("clip", "Clips uploaded", "Dashcam, Sentry and requested footage")}${rowT("problem", "Problems", "Dashcam issues, hot Pi, Starlink trouble, data plan")}${rowT("info", "Updates", "Pi updated, Starlink restarted, and similar")}${rowT("recap", "Daily recap", "One summary at 8 PM on days the car was used")}${rowT("online", "Starlink is online", "A ping when the car wakes up and the internet is ready")}${rowT("wake", "Car woke up at night", "If the car wakes between midnight and 5 AM")}
      <label class="toggle"><span><div style="font-weight:600">Quiet hours</div><div class="muted small">Hold everything except problems</div></span>
        <span class="switch"><input type="checkbox" id="quietOn" ${quiet.on ? "checked" : ""}><span></span></span></label>
      <div class="row" id="quietRow" ${quiet.on ? "" : "hidden"}><select class="input" id="quietFrom" style="flex:1" aria-label="Quiet from">${hourOpts(quiet.from)}</select><span class="muted">to</span><select class="input" id="quietTo" style="flex:1" aria-label="Quiet until">${hourOpts(quiet.to)}</select></div></div>
      <div class="row"><button class="btn" style="flex:1" id="pushTest">Send a test</button><button class="btn ghost" style="flex:1" id="pushOff">Turn off</button></div>
      <div class="muted small">${ps.devices} device${ps.devices === 1 ? "" : "s"} getting notifications.</div>`;
    const savePrefs = async () => {
      const p = {}; body.querySelectorAll("[data-pref]").forEach((x) => p[x.dataset.pref] = x.checked);
      p.quiet = { on: document.getElementById("quietOn").checked, from: Number(document.getElementById("quietFrom").value), to: Number(document.getElementById("quietTo").value) };
      document.getElementById("quietRow").hidden = !p.quiet.on;
      await api("/api/push/prefs", { method: "POST", body: { endpoint: ps.sub.endpoint, prefs: p } }).catch(() => {});
      toast("Saved");
    };
    body.querySelectorAll("[data-pref], #quietOn, #quietFrom, #quietTo").forEach((inp) => inp.onchange = savePrefs);
    document.getElementById("pushTest").onclick = async () => {
      const r = await api("/api/push/test", { method: "POST", body: {} }).catch(() => null);
      toast(r && r.results && r.results.some((x) => x.status && x.status < 300) ? "Sent! Check your notifications." : "Couldn't send. Try turning notifications off and on.");
    };
    document.getElementById("pushOff").onclick = async () => {
      await api("/api/push/unsubscribe", { method: "POST", body: { endpoint: ps.sub.endpoint } }).catch(() => {});
      await ps.sub.unsubscribe().catch(() => {});
      state.pushOn = false; toast("Notifications off"); render();
    };
  }

  // ---------- data refresh + routing ----------
  async function refresh(manual) {
    if (state.loading) return;
    state.loading = true;
    const btn = document.getElementById("btnRefresh");
    btn && btn.classList.add("spin");
    try {
      state.ov = await api("/api/overview");
      checkAppUpdate();
      const busy = document.querySelector(".scrim") || (document.activeElement && ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName));
      if (!busy) {
        if (manual || state.route === "home" || state.route === "drive") render();
        else setTitle();
      }
      if (manual) toast("Up to date");
    } catch (e) {
      if (e.message !== "auth" && manual) toast("Couldn't refresh. Check your connection.");
    } finally {
      state.loading = false;
      btn && btn.classList.remove("spin");
    }
  }
  function route() {
    const r = (location.hash || "#home").slice(1);
    state.route = TITLES[r] ? r : "home";
    window.scrollTo(0, 0);
    render();
  }

  async function boot() {
    try {
      const me = await fetch("/api/me", { credentials: "same-origin" }).then((r) => r.json());
      state.me = me;
      state.authed = me.authed;
    } catch { state.authed = false; }
    if (!state.authed) return renderLogin();
    renderShell();
    try { state.ov = await api("/api/overview"); checkAppUpdate(); } catch {}
    pushStatus().then((ps) => { state.pushOn = !!ps.on; if (state.route === "home") render(); });
    route();
  }

  window.addEventListener("hashchange", route);
  document.addEventListener("visibilitychange", () => { if (!document.hidden && state.authed) refresh(); });
  setInterval(() => { if (!document.hidden && state.authed) refresh(); }, 20000);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  boot();
})();
