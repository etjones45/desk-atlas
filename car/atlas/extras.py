"""Add-ons for the monitor (v1.2): Starlink drop log, offline catch-up, energy use, devices on the
car WiFi, the dish's sky view, speed tests and housekeeping. Each one is self-contained so a
problem in any of them can never stop the core monitor loop."""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import threading
import time
from pathlib import Path

from common import STATE_DIR, cloud, log, read_json, run, today, write_json

C = "monitor"


def guarded(name: str, fn, *args, default=None, **kwargs):
    """Run an add-on; log and carry on if it fails."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        log(C, f"{name} failed: {e}")
        return default


# ---------------------------------------------------------------- Starlink drops
class OutageLog:
    """A drop = the Starlink had service this trip, then went 30+ seconds without it."""

    def __init__(self, conn):
        self.cur_start = None
        self.cur_cause = None
        self.bad_polls = 0
        self.seen_connected = False
        self.last_saved = 0.0
        # Anything left open from before a power cut is treated as ended when we last saw it.
        conn.execute("UPDATE outages SET end = start + 30 WHERE end IS NULL")
        conn.commit()

    @staticmethod
    def cause(d: dict) -> str | None:
        if not d.get("reachable"):
            return "dish not answering"
        state = d.get("state")
        if state == "CONNECTED":
            if (d.get("drop_pct") or 0) >= 50:
                return "blocked view of the sky" if d.get("currently_obstructed") else "heavy signal loss"
            return None
        if d.get("currently_obstructed"):
            return "blocked view of the sky"
        return {"SEARCHING": "searching for satellites", "BOOTING": "dish restarting",
                "STOWED": "dish stowed", "THERMAL_SHUTDOWN": "dish too hot",
                "NO_SATS": "no satellites in view", "OBSTRUCTED": "blocked view of the sky",
                "NO_DOWNLINK": "no signal from the satellite", "NO_PINGS": "no connection to the ground station",
                }.get(str(state), "no service")

    def update(self, conn, on_starlink: bool, d: dict, synced: bool) -> dict | None:
        now = time.time()
        cause = self.cause(d) if on_starlink else None
        if on_starlink and cause is None:
            self.seen_connected = True
        if not on_starlink or not synced or not self.seen_connected or cause is None:
            self.bad_polls = 0
            if self.cur_start is not None:
                conn.execute("UPDATE outages SET end=? WHERE start=?", (now, self.cur_start))
                conn.commit()
                log(C, f"Starlink drop ended after {now - self.cur_start:.0f}s ({self.cur_cause})")
                self.cur_start = self.cur_cause = None
            return None
        self.bad_polls += 1
        if self.cur_start is None:
            if self.bad_polls >= 2:                       # two checks in a row, about 30 s
                self.cur_start = now - 15 * (self.bad_polls - 1)
                self.cur_cause = cause
                conn.execute("INSERT OR REPLACE INTO outages(start, end, cause, sent) VALUES(?,?,?,0)",
                             (self.cur_start, now, cause))
                conn.commit()
                self.last_saved = now
        elif now - self.last_saved >= 60:                 # keep "seen so far" fresh without hammering the SD card
            conn.execute("UPDATE outages SET end=? WHERE start=?", (now, self.cur_start))
            conn.commit()
            self.last_saved = now
        if self.cur_start is None:
            return None
        return {"since": self.cur_start, "cause": self.cur_cause, "seconds": round(now - self.cur_start)}

    def today_summary(self, conn) -> dict:
        t0 = time.mktime(time.strptime(today(), "%Y-%m-%d"))
        row = conn.execute("SELECT COUNT(*), COALESCE(SUM(end - start), 0) FROM outages WHERE start >= ?", (t0,)).fetchone()
        return {"count": row[0], "seconds": round(row[1])}

    def push(self, cfg, conn) -> None:
        rows = conn.execute("SELECT start, end, cause FROM outages WHERE sent=0 AND start != ? ORDER BY start LIMIT 200",
                            (self.cur_start or -1,)).fetchall()
        if not rows:
            return
        body = {"outages": [[round(r[0], 1), round(r[1] or r[0], 1), r[2]] for r in rows]}
        if cloud(cfg, "POST", "/api/pi/outages", body, timeout=15) is not None:
            conn.executemany("UPDATE outages SET sent=1 WHERE start=?", [(r[0],) for r in rows])
            conn.execute("DELETE FROM outages WHERE sent=1 AND start < ?", (time.time() - 90 * 86400,))
            conn.commit()


# ---------------------------------------------------------------- offline catch-up
def history_row(status: dict) -> dict:
    """The handful of numbers the app charts, taken from a full status report."""
    pi, d, cam = status.get("pi") or {}, status.get("starlink") or {}, status.get("teslacam") or {}
    loc = status.get("location") or {}
    return {"ts": round(status.get("updated_epoch") or time.time(), 1), "net": pi.get("network"),
            "internet": 1 if pi.get("internet") else 0, "dish_ok": 1 if d.get("reachable") else 0,
            "state": d.get("state"), "quality": d.get("quality"), "ping": d.get("ping_ms"),
            "drop_pct": d.get("drop_pct"), "obstructed": d.get("obstructed_pct"), "down": d.get("down_mbps"),
            "up": d.get("up_mbps"), "power": d.get("power_w"), "temp": pi.get("cpu_temp_c"),
            "load1": pi.get("load1"), "wifi_signal": pi.get("wifi_signal"), "gadget": cam.get("gadget"),
            "usb_link": cam.get("usb_link"),
            "lat": None if loc.get("stale") else loc.get("lat"), "lon": None if loc.get("stale") else loc.get("lon")}


class Backlog:
    """While the app can't be reached (no internet), keep one reading a minute and send them later,
    so the charts show what happened during the gap instead of a hole."""

    def __init__(self):
        self.last_kept = 0.0

    def keep(self, conn, status: dict) -> None:
        if time.time() - self.last_kept < 60:
            return
        self.last_kept = time.time()
        row = history_row(status)
        conn.execute("INSERT OR REPLACE INTO backlog(ts, row) VALUES(?,?)", (row["ts"], json.dumps(row)))
        conn.execute("DELETE FROM backlog WHERE ts < ?", (time.time() - 3 * 86400,))
        conn.commit()

    @staticmethod
    def flush(cfg, conn) -> int:
        rows = conn.execute("SELECT ts, row FROM backlog ORDER BY ts LIMIT 240").fetchall()
        if not rows:
            return 0
        body = {"rows": [json.loads(r[1]) for r in rows]}
        if cloud(cfg, "POST", "/api/pi/history", body, timeout=20) is None:
            return 0
        conn.executemany("DELETE FROM backlog WHERE ts=?", [(r[0],) for r in rows])
        conn.commit()
        return len(rows)


# ---------------------------------------------------------------- energy
class Energy:
    """Adds up how much energy the Starlink has used today (watt-hours)."""

    def __init__(self, mon_state_path: Path):
        self.path = mon_state_path
        e = (read_json(mon_state_path, {}) or {}).get("energy") or {}
        self.day = e.get("day") or today()
        self.wh = float(e.get("wh") or 0) if self.day == today() else 0.0
        self.day = today()
        self.last = time.time()
        self.saved = time.time()

    def add(self, power_w, dish_on: bool) -> float:
        now = time.time()
        dt = min(now - self.last, 60)
        self.last = now
        if today() != self.day:
            self.day, self.wh = today(), 0.0
        if dish_on and isinstance(power_w, (int, float)) and 0 < power_w < 200:
            self.wh += power_w * dt / 3600
        if now - self.saved > 300:
            self.saved = now
            st = read_json(self.path, {}) or {}
            st["energy"] = {"day": self.day, "wh": round(self.wh, 2)}
            write_json(self.path, st)
        return round(self.wh, 1)


# ---------------------------------------------------------------- devices on the car WiFi
def count_devices() -> dict | None:
    """How many phones/tablets/laptops are on the same WiFi as the Pi (needs arp-scan)."""
    if not shutil.which("arp-scan"):
        return None
    code, out = run(["ip", "-o", "-4", "route", "show", "default"], timeout=5)
    m = re.search(r"default via (\S+) dev (\S+)", out or "")
    if code != 0 or not m:
        return None
    gateway, iface = m.group(1), m.group(2)
    code, out = run(["arp-scan", "-l", "-I", iface, "-q", "-x", "-r", "2", "-t", "300"], timeout=15)
    if code != 0:
        return None
    seen = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and re.fullmatch(r"\d+\.\d+\.\d+\.\d+", parts[0]) and parts[0] != gateway:
            seen.add(parts[1].lower())
    return {"count": len(seen), "at": time.time()}


# ---------------------------------------------------------------- the dish's view of the sky
def push_skymap(cfg, starlink_grpc, ctx) -> bool:
    """Send the dish's obstruction map (which parts of the sky it can see) to the app."""
    rows = starlink_grpc.obstruction_map(context=ctx)
    h = len(rows)
    w = len(rows[0]) if h else 0
    if not w or w * h > 40000:
        return False
    buf = bytearray()
    known = 0
    for r in rows:
        for v in r:
            if v is None or v < 0:
                buf.append(255)                 # no data for that patch of sky yet
            else:
                buf.append(max(0, min(254, int(v * 254))))
                known += 1
    body = {"w": w, "h": h, "known": known, "at": time.time(), "data": base64.b64encode(bytes(buf)).decode()}
    return cloud(cfg, "POST", "/api/pi/skymap", body, timeout=20) is not None


# ---------------------------------------------------------------- speed test
class SpeedRunner:
    """Runs speed tests in the background so the monitor keeps checking everything else meanwhile."""

    def __init__(self, mon_state_path: Path):
        self.path = mon_state_path
        self.thread: threading.Thread | None = None
        self.last = (read_json(mon_state_path, {}) or {}).get("speedtest")

    def busy(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def ran_today(self) -> bool:
        return bool(self.last and time.strftime("%Y-%m-%d", time.localtime(self.last.get("at", 0))) == today())

    def start(self, cfg, profile: str, network: str, command_id=None, auto: bool = False) -> bool:
        if self.busy():
            return False
        self.thread = threading.Thread(target=self._run, args=(cfg, profile, network, command_id, auto), daemon=True)
        self.thread.start()
        return True

    def _run(self, cfg, profile, network, command_id, auto) -> None:
        try:
            import speedcheck
            res = speedcheck.run_test(profile)
        except Exception as e:  # noqa: BLE001
            res = {"ok": False, "at": time.time(), "profile": profile, "error": str(e)[:120]}
        res.update({"network": network, "auto": bool(auto)})
        if res.get("ok") or auto:
            # Remember failed automatic tests too, so one bad moment doesn't mean retrying all day.
            self.last = res
            st = read_json(self.path, {}) or {}
            st["speedtest"] = res
            write_json(self.path, st)
        if res.get("ok"):
            log(C, f"speed test ({profile}): {res.get('down_mbps')} down / {res.get('up_mbps')} up / {res.get('ping_ms')} ms")
            cloud(cfg, "POST", "/api/pi/speedtest", res, timeout=15)
        if command_id:
            msg = (f"{res.get('down_mbps')} Mbps down · {res.get('up_mbps')} Mbps up · {res.get('ping_ms')} ms"
                   if res.get("ok") else f"Speed test didn't finish: {res.get('error')}")
            cloud(cfg, "POST", f"/api/pi/commands/{command_id}", {"ok": bool(res.get("ok")), "result": msg}, timeout=15)


# ---------------------------------------------------------------- housekeeping
def housekeeping() -> dict:
    """Small protections for a Pi that may stay on for days in Sentry Mode."""
    out: dict = {}
    # 1) /var/log on this board is a small RAM disk. If it fills up, services start failing.
    try:
        st = os.statvfs("/var/log")
        used = 1 - st.f_bavail / st.f_blocks if st.f_blocks else 0
        own_disk = os.path.ismount("/var/log")
        if own_disk:
            out["log_used_pct"] = round(100 * used)
        if own_disk and used > 0.85:
            for name in ("syslog", "kern.log", "messages", "daemon.log", "debug", "user.log"):
                p = Path("/var/log") / name
                if p.is_file() and p.stat().st_size > 1_000_000:
                    with open(p, "w"):
                        pass
            run(["journalctl", "--vacuum-size=10M"], timeout=30)
            out["logs_trimmed"] = True
            log(C, f"/var/log was {out['log_used_pct']}% full; trimmed old logs")
    except OSError:
        pass
    # 2) Known Orange Pi Zero 2W quirk: an empty USB port can look like a broken device and retry forever
    #    ("error -62"), filling the log. If that's happening and nothing is plugged into that port, switch it off
    #    until the next restart.
    try:
        code, dm = run(["dmesg"], timeout=5)
        if code == 0:
            up = float(Path("/proc/uptime").read_text().split()[0])
            hits: dict = {}
            for m in re.finditer(r"^\[\s*(\d+\.\d+)\] usb (\d+)-(\d+): device descriptor read/64, error -62", dm, re.M):
                if up - float(m.group(1)) < 600:
                    hits[m.group(2)] = hits.get(m.group(2), 0) + 1
            for bus, n in hits.items():
                if n < 15:
                    continue
                root = Path(os.path.realpath(f"/sys/bus/usb/devices/usb{bus}"))
                ctrl = root.parent
                real_devices = [p for p in Path("/sys/bus/usb/devices").glob(f"{bus}-*") if ":" not in p.name
                                and (p / "idVendor").exists()]
                drv = ctrl / "driver"
                if real_devices or not drv.exists():
                    continue
                drv_name = os.path.basename(os.path.realpath(drv))
                Path(f"/sys/bus/platform/drivers/{drv_name}/unbind").write_text(ctrl.name)
                out["usb_port_quieted"] = ctrl.name
                log(C, f"quieted empty USB port {ctrl.name} ({n} failed tries in 10 min)")
    except (OSError, ValueError):
        pass
    return out


def system_snapshot() -> str:
    """Plain-text look at what the Pi is busy with (for the app's Diagnostics)."""
    parts = []
    for title, cmd in (("Uptime and load", ["uptime"]),
                       ("Busiest processes", ["bash", "-c", "ps -eo pcpu,pmem,etime,comm --sort=-pcpu | head -12"]),
                       ("Memory", ["free", "-m"]),
                       ("Storage", ["df", "-h", "/", "/var/log", "/run"]),
                       ("Temperature", ["bash", "-c", "awk '{printf \"%.1f C\\n\", $1/1000}' /sys/class/thermal/thermal_zone0/temp"]),
                       ("WiFi", ["bash", "-c", "nmcli -t -f ACTIVE,SSID,SIGNAL,RATE dev wifi | grep '^yes'; iw dev 2>/dev/null | grep -E 'Interface|ssid|channel|txpower'"]),
                       ("USB devices", ["bash", "-c", "lsusb 2>/dev/null || ls /sys/bus/usb/devices"]),
                       ("Kernel warnings (last 15)", ["bash", "-c", "dmesg --level=err,warn 2>/dev/null | grep -v 'unknown read' | tail -15"]),
                       ("Failed services", ["bash", "-c", "systemctl --failed --no-legend | head -8"])):
        code, out = run(cmd, timeout=10)
        parts.append(f"== {title}\n{(out or '').strip()[:1500]}")
    return "\n\n".join(parts)


OUTPUT_COMMANDS = {
    "doctor": "Health check",
    "usb_debug": "USB deep check",
    "logs": "Recent logs",
    "sysinfo": "What the Pi is busy with",
}


def run_output_command(kind: str, scripts_dir: Path) -> tuple[bool, str]:
    if kind == "doctor":
        code, out = run([str(scripts_dir / "doctor.sh")], timeout=90)
    elif kind == "usb_debug":
        code, out = run([str(scripts_dir / "usb-debug.sh")], timeout=60)
    elif kind == "logs":
        code, out = run(["journalctl", "-u", "car-atlas-teslacam", "-u", "car-atlas-uploader", "-u", "car-atlas-monitor",
                         "-u", "car-atlas-update", "-u", "car-atlas-tune", "-n", "150", "--no-pager", "-o", "short"], timeout=30)
    elif kind == "sysinfo":
        code, out = 0, system_snapshot()
    else:
        return False, "unknown"
    out = re.sub(r"\x1b\[[0-9;]*m", "", out or "")
    return code == 0, out[-15000:]


__all__ = ["OutageLog", "Backlog", "Energy", "SpeedRunner", "count_devices", "push_skymap", "housekeeping",
           "guarded", "history_row", "run_output_command", "OUTPUT_COMMANDS", "STATE_DIR"]
