"""Shared helpers for Car Atlas: config, paths, state, networking, rclone, alerts."""
from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
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
    }


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
        """
    )
    return conn


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
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
        cloud(cfg, "POST", "/api/pi/alert", {"title": title, "message": message, "category": category,
                                              "link": "/#footage" if category == "clip" else "/#home"})
    if (cfg.get("NTFY_TOPIC") or "").strip():
        notify(cfg, title, message, key=None, tags=tags, click=click)
    else:
        record_alert_locally(title, message)


def today() -> str:
    return time.strftime("%Y-%m-%d", time.localtime())


def clock_synced() -> bool:
    code, out = run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], timeout=5)
    return code == 0 and out.strip() == "yes"
