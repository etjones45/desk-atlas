"""Shared helpers for Car Atlas: config, paths, state, networking, rclone, alerts."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent          # .../car
STATE_DIR = Path(os.environ.get("CAR_ATLAS_STATE", "/var/lib/car-atlas"))
RUN_DIR = Path(os.environ.get("CAR_ATLAS_RUN", "/run/car-atlas"))
ETC_DIR = Path(os.environ.get("CAR_ATLAS_ETC", "/etc/car-atlas"))
RCLONE_CONF = ETC_DIR / "rclone.conf"
DB_PATH = STATE_DIR / "atlas.db"


def log(component: str, msg: str) -> None:
    print(f"[{component}] {msg}", flush=True)


def read_text(path, default=None):
    try:
        return Path(path).read_text().replace("\x00", "").strip()
    except (OSError, UnicodeDecodeError):
        return default


def version() -> str:
    return read_text(SRC_DIR / "VERSION", "unknown") or "unknown"


def git_sha() -> str | None:
    code, out = run(["git", "-C", str(SRC_DIR.parent), "rev-parse", "--short", "HEAD"], timeout=5)
    return out.strip() if code == 0 else None


USB0_DR_MODE = "/sys/firmware/devicetree/base/soc/usb@5100000/dr_mode"
ORANGEPI_ENV = Path("/boot/orangepiEnv.txt")


def usb_info() -> dict:
    """What the dashcam USB connection looks like right now (cheap: only reads small files)."""
    gadget = read_json(RUN_DIR / "gadget.json", {}) or {}
    udcs = sorted(p.name for p in Path("/sys/class/udc").glob("*")) if Path("/sys/class/udc").exists() else []
    udc = gadget.get("udc") or (udcs[0] if udcs else None)
    state = read_text(f"/sys/class/udc/{udc}/state") if udc else None
    speed = read_text(f"/sys/class/udc/{udc}/current_speed") if udc else None
    env = {}
    for line in (read_text(ORANGEPI_ENV, "") or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    overlays = (env.get("overlays", "") + " " + env.get("user_overlays", "")).split()
    otg_role = None
    for p in Path("/sys/devices/platform").glob("soc*/*usbc0*/otg_role"):
        otg_role = read_text(p)
        break
    bound = read_text("/sys/kernel/config/usb_gadget/teslacam/UDC")
    img = load_config().get("TESLACAM_IMAGE", "/var/lib/car-atlas/teslacam.img")
    return {
        "gadget": gadget.get("gadget", "unknown"),
        "detail": gadget.get("detail"),
        "udc": udc,
        "udcs": udcs,
        "bound": bool(bound),
        "state": state,
        "speed": speed,
        "car_connected": state == "configured",
        "dr_mode": read_text(USB0_DR_MODE),
        "otg_role": otg_role,
        "usb0_host_overlay": any("usb0-host" in o for o in overlays),
        "otg_fix_installed": any("car-atlas-usb0-otg" in o for o in overlays),
        "image_gb": round(os.path.getsize(img) / 1e9, 1) if os.path.exists(img) else None,
        # The car writing video to the drive bumps the image file's modified time.
        "last_write_epoch": _mtime(img),
    }


def _mtime(path: str) -> float | None:
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def cpu_temp() -> float | None:
    try:
        return round(int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000, 1)
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- settings from the app
# The app (car.etjarvis.com) owns these. The Pi gets them with every check-in and keeps a copy
# on disk so they still apply when it's offline.
SETTINGS_FILE = STATE_DIR / "app_settings.json"
DEFAULT_SETTINGS = {
    "uploads_paused": False,        # hold all footage uploads
    "uploads_on_starlink": True,    # upload saved dashcam clips over Starlink
    "sentry_on_starlink": True,     # upload Sentry events over Starlink
    "starlink_cap_mb": 5000,        # footage per day over Starlink
    "starlink_speed": "normal",     # slow | normal | fast | max
    "auto_speedtest": True,         # one small speed test a day on Starlink
    "retention_days": 0,            # delete Drive footage older than this (0 = keep forever)
    "heat_protect": True,           # pause uploads while the Pi is hot
    "plan_protect": True,           # hold Starlink uploads when the data plan is nearly used
    "plan_pct": None,               # filled in by the app: % of this month's data plan used
}
SPEED_LIMITS = {"slow": "190k", "normal": "375k", "fast": "1M", "max": "0"}


def app_settings() -> dict:
    out = dict(DEFAULT_SETTINGS)
    saved = read_json(SETTINGS_FILE, {}) or {}
    for k, default in DEFAULT_SETTINGS.items():
        v = saved.get(k)
        if v is None:
            continue
        if isinstance(default, bool):
            out[k] = bool(v)
        elif isinstance(default, int) and not isinstance(default, bool):
            try:
                out[k] = int(v)
            except (TypeError, ValueError):
                pass
        else:
            out[k] = v
    out["rev"] = saved.get("rev")
    return out


def save_app_settings(new: dict) -> bool:
    """Store settings sent by the app. Returns True when something changed."""
    if not isinstance(new, dict):
        return False
    cur = read_json(SETTINGS_FILE, {}) or {}
    keep = {k: new[k] for k in list(DEFAULT_SETTINGS) + ["rev"] if k in new}
    if keep == cur:
        return False
    write_json(SETTINGS_FILE, keep)
    return True


def usb_lowlevel(udc: str | None) -> dict:
    """What the USB chip itself reports (root only; cheap). Helps tell a bad cable from a Pi-side problem."""
    out: dict = {}
    if not udc:
        return out
    dev = os.path.realpath(f"/sys/class/udc/{udc}/device")
    out["otg_state"] = read_text(f"{dev}/mode")
    out["vbus"] = read_text(f"{dev}/vbus")
    # Note: don't read the musb regdump here; on sunxi it floods the kernel log ("unknown readw offset").
    v = out.get("vbus") or ""
    out["vbus_on"] = ("Vbus on" in v) if v else None
    try:
        for line in Path("/proc/interrupts").read_text().splitlines():
            if "musb" in line.lower():
                parts = line.split()
                ncpu = os.cpu_count() or 4  # columns after "NNN:" are per-CPU counts, then the controller info
                out["irq_count"] = sum(int(x) for x in parts[1:1 + ncpu] if x.isdigit())
                break
    except OSError:
        pass
    ext = {}
    for e in Path("/sys/class/extcon").glob("*") if Path("/sys/class/extcon").exists() else []:
        ext[read_text(e / "name") or e.name] = (read_text(e / "state") or "").replace("\n", " ")
    if ext:
        out["extcon"] = ext
    return out


def usb_kernel_log(lines: int = 12) -> list[str]:
    code, out = run(["dmesg"], timeout=5)
    if code != 0:
        return []
    keep = [ln for ln in out.splitlines()
            if any(k in ln.lower() for k in ("musb", "sun4i-usb", "udc", "gadget", "mass_storage", "vbus", "extcon", "5100000.usb"))
            and "unknown read" not in ln and "unknown write" not in ln]
    return [ln[:180] for ln in keep[-lines:]]


def loop_partition(loop: str) -> str:
    """The car's filesystem: partition 1 if the image has a partition table, else the whole image."""
    for _ in range(10):
        if os.path.exists(loop + "p1"):
            return loop + "p1"
        time.sleep(0.3)
    return loop


def _first_partition(image: str) -> tuple[int, int] | None:
    """(start_bytes, size_bytes) of partition 1 from the image's partition table, if it has one."""
    code, out = run(["sfdisk", "-J", image], timeout=15)
    if code != 0:
        return None
    try:
        t = json.loads(out)["partitiontable"]
        p = t["partitions"][0]
        sector = int(t.get("sectorsize", 512))
        return int(p["start"]) * sector, int(p["size"]) * sector
    except (ValueError, KeyError, IndexError, TypeError):
        return None


def attach_image(image: str, read_only: bool = True) -> tuple[str | None, list[str]]:
    """Attach the dashcam image as a block device. Returns (filesystem_device, loops_to_detach).

    Uses the kernel's partition node (loopNp1) when it shows up, and falls back to mapping
    partition 1 by its byte offset, so it works even if partition scanning isn't available.
    """
    ro = ["-r"] if read_only else []
    code, out = run(["losetup", *ro, "-P", "-f", "--show", image])
    if code != 0:
        log("common", f"losetup failed: {out.strip()}")
        return None, []
    loop = out.strip().splitlines()[-1]
    part = loop_partition(loop)
    if part != loop:
        return part, [loop]
    span = _first_partition(image)
    if span:
        code, out = run(["losetup", *ro, "-f", "--show", "-o", str(span[0]), "--sizelimit", str(span[1]), image])
        if code == 0:
            p = out.strip().splitlines()[-1]
            return p, [p, loop]
    return loop, [loop]


def detach_loops(loops: list[str]) -> None:
    for lp in loops:
        run(["losetup", "-d", lp])


def fs_type(device: str) -> str | None:
    code, out = run(["blkid", "-o", "value", "-s", "TYPE", device], timeout=10)
    return out.strip() or None if code == 0 else None


def _read_env(path: Path) -> dict:
    out = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return out


def load_config() -> dict:
    cfg = _read_env(SRC_DIR / "config.default.env")
    cfg.update(_read_env(ETC_DIR / "config.env"))
    return cfg


def cfg_int(cfg: dict, key: str, default: int) -> int:
    try:
        return int(str(cfg.get(key, default)).strip())
    except ValueError:
        return default


def ensure_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)


def db() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS samples(
            ts REAL, lat REAL, lon REAL, state TEXT, ping_ms REAL, drop_pct REAL,
            obstructed INTEGER, down_mbps REAL, up_mbps REAL);
        CREATE INDEX IF NOT EXISTS samples_ts ON samples(ts);
        CREATE TABLE IF NOT EXISTS coverage(
            ts REAL, lat REAL, lon REAL, quality TEXT, ping_ms REAL, drop_pct REAL);
        CREATE INDEX IF NOT EXISTS coverage_ts ON coverage(ts);
        CREATE TABLE IF NOT EXISTS usage(day TEXT PRIMARY KEY, down_bytes INTEGER, up_bytes INTEGER);
        CREATE TABLE IF NOT EXISTS uploads(
            kind TEXT, folder TEXT, sig TEXT, bytes INTEGER, uploaded_at REAL, network TEXT,
            PRIMARY KEY(kind, folder));
        CREATE TABLE IF NOT EXISTS upload_budget(day TEXT PRIMARY KEY, starlink_bytes INTEGER);
        CREATE TABLE IF NOT EXISTS outages(
            start REAL PRIMARY KEY, end REAL, cause TEXT, sent INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS backlog(ts REAL PRIMARY KEY, row TEXT);
        """
    )
    return conn


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):          # missing, unreadable, not JSON, or binary (encrypted) data
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, default=str))
    os.replace(tmp, path)


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 124, str(e)


def wifi_info() -> dict:
    """Current WiFi network name and signal strength (0-100)."""
    code, out = run(["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL", "dev", "wifi"], timeout=10)
    if code == 0:
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[0] == "yes":
                try:
                    sig = int(parts[-1])
                except ValueError:
                    sig = None
                return {"ssid": ":".join(parts[1:-1]), "signal": sig}
    return {"ssid": None, "signal": None}


def network_kind(cfg: dict, ssid: str | None) -> str:
    if not ssid:
        return "none"
    if ssid == cfg.get("STARLINK_SSID"):
        return "starlink"
    if ssid == cfg.get("HOME_SSID"):
        return "home"
    return "other"


def internet_up(timeout: float = 4.0) -> bool:
    for host in ("www.googleapis.com", "1.1.1.1"):
        try:
            with socket.create_connection((host, 443), timeout=timeout):
                return True
        except OSError:
            continue
    return False


def drive_ready() -> bool:
    return RCLONE_CONF.is_file() and "[gdrive]" in RCLONE_CONF.read_text()


def drive_remote(folder_id: str, path: str = "") -> str:
    return f"gdrive,root_folder_id={folder_id}:{path}"


def rclone(args: list[str], timeout: int = 120, bwlimit: str | None = None) -> tuple[int, str]:
    cmd = ["rclone", "--config", str(RCLONE_CONF), "--retries", "3",
           "--low-level-retries", "10", "--contimeout", "20s", "--timeout", "60s"]
    if bwlimit and bwlimit != "0":
        cmd += ["--bwlimit", bwlimit]
    return run(cmd + args, timeout=timeout)


def rclone_out(args: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """rclone where the answer is read by code: returns (code, stdout, stderr) kept apart, so rclone's
    own notices can never be mistaken for data."""
    cmd = ["rclone", "--config", str(RCLONE_CONF), "--retries", "3", "--low-level-retries", "10",
           "--contimeout", "20s", "--timeout", "60s"]
    try:
        p = subprocess.run(cmd + args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 124, "", str(e)


def rclone_progress(args: list[str], timeout: int = 6 * 3600, bwlimit: str | None = None,
                    on_stats=None) -> tuple[int, str]:
    """Like rclone(), but calls on_stats({"bytes","total","speed","eta"}) every ~15 s while it runs."""
    cmd = ["rclone", "--config", str(RCLONE_CONF), "--retries", "3", "--low-level-retries", "10",
           "--contimeout", "20s", "--timeout", "60s",
           "--stats", "15s", "--use-json-log", "--stats-log-level", "NOTICE"]
    if bwlimit and bwlimit != "0":
        cmd += ["--bwlimit", bwlimit]
    tail: list[str] = []
    try:
        p = subprocess.Popen(cmd + args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError as e:
        return 124, str(e)
    deadline = time.time() + timeout
    killer = threading.Timer(timeout, p.kill)
    killer.daemon = True
    killer.start()
    try:
        for line in p.stderr:              # ends when rclone exits (or is killed at the deadline)
            line = line.strip()
            if not line:
                continue
            try:
                j = json.loads(line)
            except ValueError:
                tail.append(line[:300])
                continue
            st = j.get("stats")
            if st and on_stats:
                try:
                    on_stats({"bytes": st.get("bytes") or 0, "total": st.get("totalBytes") or 0,
                              "speed": st.get("speed") or 0, "eta": st.get("eta")})
                except Exception:  # noqa: BLE001 - progress is a nicety
                    pass
            elif not st:
                tail.append(str(j.get("msg", ""))[:300])
            del tail[:-8]
        code = p.wait(timeout=30)
    except Exception as e:  # noqa: BLE001
        p.kill()
        return 124, str(e)
    finally:
        killer.cancel()
    if time.time() >= deadline and code != 0:
        return 124, "timed out"
    return code, "\n".join(tail)


def notify(cfg: dict, title: str, message: str, key: str | None = None,
           cooldown_s: int = 3600, tags: str = "", click: str = "") -> bool:
    """Send a push alert via ntfy. `key` + cooldown prevents repeats."""
    topic = (cfg.get("NTFY_TOPIC") or "").strip()
    if not topic:
        return False
    sent_path = STATE_DIR / "alerts_sent.json"
    sent = read_json(sent_path, {}) or {}
    now = time.time()
    if key and now - sent.get(key, 0) < cooldown_s:
        return False
    url = (cfg.get("NTFY_SERVER") or "https://ntfy.sh").rstrip("/") + "/" + topic
    req = urllib.request.Request(url, data=message.encode(), method="POST")
    req.add_header("Title", title)
    if tags:
        req.add_header("Tags", tags)
    if click:
        req.add_header("Click", click)
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:  # noqa: BLE001 - alerts are best-effort
        log("notify", f"failed: {e}")
        return False
    if key:
        sent[key] = now
        write_json(sent_path, sent)
    recent = read_json(STATE_DIR / "alerts_recent.json", []) or []
    recent.insert(0, {"at": now, "title": title, "message": message})
    write_json(STATE_DIR / "alerts_recent.json", recent[:20])
    return True


def record_alert_locally(title: str, message: str) -> None:
    """Keep a short alert history even when no ntfy topic is set."""
    recent = read_json(STATE_DIR / "alerts_recent.json", []) or []
    if recent and recent[0].get("title") == title and time.time() - recent[0].get("at", 0) < 3600:
        return
    recent.insert(0, {"at": time.time(), "title": title, "message": message})
    write_json(STATE_DIR / "alerts_recent.json", recent[:20])


def cloud_ready(cfg: dict) -> bool:
    return bool((cfg.get("CLOUD_URL") or "").strip() and (cfg.get("CLOUD_KEY") or "").strip())


def cloud(cfg: dict, method: str, path: str, data=None, timeout: int = 20):
    """Talk to car.etjarvis.com. Returns parsed JSON, or None if it didn't work."""
    if not cloud_ready(cfg):
        return None
    url = cfg["CLOUD_URL"].rstrip("/") + path
    body = json.dumps(data, default=str).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", "Bearer " + cfg["CLOUD_KEY"].strip())
    req.add_header("User-Agent", "car-atlas-pi")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except Exception as e:  # noqa: BLE001 - cloud is best-effort
        log("cloud", f"{method} {path} failed: {e}")
        return None


def alert(cfg: dict, title: str, message: str, key: str, cooldown_s: int = 3600,
          tags: str = "", click: str = "", category: str = "problem", to_cloud: bool = True) -> None:
    """Raise an alert once per cooldown: to the app (push notification), ntfy if set, and the local log."""
    sent_path = STATE_DIR / "alerts_sent.json"
    sent = read_json(sent_path, {}) or {}
    now = time.time()
    if key and now - sent.get(key, 0) < cooldown_s:
        return
    if key:
        sent[key] = now
        write_json(sent_path, sent)
    if to_cloud and cloud_ready(cfg):
        payload = {"title": title, "message": message, "category": category, "at": now,
                   "link": "/#footage" if category == "clip" else "/#home"}
        if cloud(cfg, "POST", "/api/pi/alert", payload) is None:
            queue_for_cloud("/api/pi/alert", payload)
    if (cfg.get("NTFY_TOPIC") or "").strip():
        notify(cfg, title, message, key=None, tags=tags, click=click)
    else:
        record_alert_locally(title, message)


OUTBOX = STATE_DIR / "outbox.json"


def queue_for_cloud(path: str, payload: dict) -> None:
    """Couldn't reach the app (no internet). Keep it and send it when we're back online."""
    box = read_json(OUTBOX, []) or []
    box.append({"path": path, "data": payload, "at": time.time()})
    write_json(OUTBOX, box[-60:])


def flush_outbox(cfg: dict) -> int:
    box = read_json(OUTBOX, []) or []
    if not box:
        return 0
    sent = 0
    while box:
        item = box[0]
        if time.time() - item.get("at", 0) > 3 * 86400:      # too old to matter
            box.pop(0)
            continue
        if cloud(cfg, "POST", item["path"], item["data"], timeout=15) is None:
            break
        box.pop(0)
        sent += 1
    write_json(OUTBOX, box)
    return sent


def today() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


def clock_synced() -> bool:
    code, out = run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], timeout=5)
    return code == 0 and out.strip() == "yes"
