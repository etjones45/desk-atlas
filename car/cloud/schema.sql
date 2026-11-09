-- Car Atlas database (Cloudflare D1)
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT, updated REAL);
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, created REAL, expires REAL, label TEXT);
CREATE TABLE IF NOT EXISTS login_attempts (ip TEXT, ts REAL);
CREATE INDEX IF NOT EXISTS login_attempts_ip ON login_attempts(ip, ts);
CREATE TABLE IF NOT EXISTS history (
  ts REAL PRIMARY KEY, net TEXT, internet INTEGER, dish_ok INTEGER, state TEXT, quality TEXT,
  ping REAL, drop_pct REAL, obstructed REAL, down REAL, up REAL, power REAL,
  temp REAL, load1 REAL, wifi_signal INTEGER, gadget TEXT, usb_link TEXT, lat REAL, lon REAL);
CREATE TABLE IF NOT EXISTS usage_daily (day TEXT PRIMARY KEY, down_mb REAL, up_mb REAL, clips_mb REAL);
CREATE TABLE IF NOT EXISTS coverage (ts REAL, lat REAL, lon REAL, q TEXT, ping REAL, drop_pct REAL, PRIMARY KEY (ts, lat, lon));
CREATE INDEX IF NOT EXISTS coverage_ts ON coverage(ts);
CREATE TABLE IF NOT EXISTS clips (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, folder TEXT, drive_id TEXT, drive_url TEXT,
  size_mb REAL, reason TEXT, city TEXT, lat REAL, lon REAL, event_ts TEXT, uploaded_at REAL,
  network TEXT, thumb BLOB, thumb_type TEXT, UNIQUE(kind, folder));
CREATE INDEX IF NOT EXISTS clips_uploaded ON clips(uploaded_at);
CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL, title TEXT, message TEXT, category TEXT, link TEXT);
CREATE TABLE IF NOT EXISTS commands (
  id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, args TEXT, status TEXT,
  created REAL, picked REAL, done REAL, result TEXT);
CREATE TABLE IF NOT EXISTS push_subs (endpoint TEXT PRIMARY KEY, p256dh TEXT, auth TEXT, label TEXT, created REAL, last_ok REAL, prefs TEXT);
CREATE TABLE IF NOT EXISTS pairing (code TEXT PRIMARY KEY, expires REAL, used INTEGER);
