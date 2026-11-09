"""Watches the Pi, the dashcam USB link, the Starlink and (optional) USB GPS.
Logs coverage, reports to car.etjarvis.com, runs commands from the app, and publishes a
status file to Google Drive (Tesla Footage/Pi Status/status.txt) as a backup.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (RUN_DIR, SRC_DIR, STATE_DIR, alert, cfg_int, clock_synced, cloud,  # noqa: E402
                    cloud_ready, db, drive_ready, drive_remote, git_sha, internet_up, load_config, log,
                    network_kind, rclone, read_json, read_text, run, today, usb_info, usb_kernel_log, usb_lowlevel, version,
                    wifi_info, write_json)
from gps import GPSReader  # noqa: E402

C = "monitor"
STATUS_LOCAL = STATE_DIR / "status.json"
REQ_DIR = STATE_DIR / "requests"
CLOUD_STATE = STATE_DIR / "cloud_state.json"
MON_STATE = STATE_DIR / "monitor_state.json"
GADGET_SH = str(SRC_DIR / "scripts" / "teslacam-gadget.sh")
USB_FIX_SH = str(SRC_DIR / "scripts" / "usb-fix.sh")

try:
    import starlink_grpc  # type: ignore
except Exception:  # noqa: BLE001
    starlink_grpc = None


# ---------------------------------------------------------------- Pi health
class PiHealth:
    """Fast numbers every loop; slower checks (services, Tailscale, git) once a minute."""

    def __init__(self):
        self.slow: dict = {}
        self.slow_at = 0.0

    def get(self) -> dict:
        out: dict = {"hostname": os.uname().nodename}
        try:
            out["cpu_temp_c"] = round(int(Path("/sys/class/thermal/thermal_zone0/temp").read_text()) / 1000, 1)
        except (OSError, ValueError):
            out["cpu_temp_c"] = None
        try:
            out["uptime_s"] = int(float(Path("/proc/uptime").read_text().split()[0]))
        except (OSError, ValueError):
            out["uptime_s"] = None
        out["load1"] = round(os.getloadavg()[0], 2)
        try:
            mem = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                k, v = line.split(":", 1)
                mem[k] = int(v.split()[0])
            out["mem_used_pct"] = round(100 * (1 - mem["MemAvailable"] / mem["MemTotal"]), 1)
        except (OSError, KeyError, ValueError):
            out["mem_used_pct"] = None
        out["sd_free_gb"] = round(shutil.disk_usage("/").free / 1e9, 1)
        freq = read_text("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
        out["cpu_mhz"] = int(freq) // 1000 if freq and freq.isdigit() else None
        out["cpu_governor"] = read_text("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
        if time.time() - self.slow_at > 60:
            self.slow_at = time.time()
            code, ts = run(["tailscale", "ip", "-4"], timeout=5)
            svc = {}
            for name in ("car-atlas-teslacam", "car-atlas-uploader", "car-atlas-monitor", "tailscaled"):
                _, s = run(["systemctl", "is-active", name], timeout=5)
                svc[name] = s.strip() or "unknown"
            self.slow = {
                "tailscale_ip": ts.strip().splitlines()[0] if code == 0 and ts.strip() else None,
                "code_version": git_sha(),
                "services": svc,
                "clock_synced": clock_synced(),
                "timezone": os.path.realpath("/etc/localtime").split("zoneinfo/")[-1],
            }
        out.update(self.slow)
        out["version"] = version()
        out["update"] = read_json(STATE_DIR / "update.json", {}) or {}
        return out


# ---------------------------------------------------------------- Starlink
class Dish:
    def __init__(self):
        self.ctx = starlink_grpc.ChannelContext() if starlink_grpc else None
        self.last_ok = 0.0
        self.last = {}
        self.history_start = None
        self.last_usage_poll = 0.0
        self.power_w = None
        self.bad_since = None
        self.last_reboot = 0.0
        self.location_supported = True

    def poll(self) -> dict:
        if not self.ctx:
            return {"reachable": False, "error": "starlink library missing"}
        try:
            status, obstruction, alerts = starlink_grpc.status_data(context=self.ctx)
        except Exception as e:  # noqa: BLE001
            self.ctx.close()
            self.ctx = starlink_grpc.ChannelContext()
            d = dict(self.last)
            d.update({"reachable": False, "error": str(e)[:160]})
            return d
        self.last_ok = time.time()
        d = {
            "reachable": True,
            "state": status.get("state"),
            "ping_ms": _r(status.get("pop_ping_latency_ms"), 0),
            "drop_pct": _r(100 * (status.get("pop_ping_drop_rate") or 0), 1),
            "obstructed_pct": _r(100 * (status.get("fraction_obstructed") or 0), 1),
            "currently_obstructed": status.get("currently_obstructed"),
            "down_mbps": _r((status.get("downlink_throughput_bps") or 0) / 1e6, 2),
            "up_mbps": _r((status.get("uplink_throughput_bps") or 0) / 1e6, 2),
            "uptime_s": status.get("uptime"),
            "software": status.get("software_version"),
            "hardware": status.get("hardware_version"),
            "gps_sats": status.get("gps_sats"),
            "alerts": sorted(k.replace("alert_", "") for k, v in (alerts or {}).items() if v),
            "location": None,
        }
        # Starlink removed dish location from the local API in May 2026. Try (cheaply) in case it returns.
        if self.location_supported:
            try:
                loc = starlink_grpc.location_data(context=self.ctx)
                if loc.get("latitude") is not None:
                    d["location"] = {"lat": round(loc["latitude"], 5), "lon": round(loc["longitude"], 5)}
                else:
                    self.location_supported = False
            except Exception:  # noqa: BLE001
                self.location_supported = False
        self.poll_usage()
        d["power_w"] = self.power_w
        self.last = d
        return d

    def poll_usage(self) -> None:
        if time.time() - self.last_usage_poll < 300:
            return
        self.last_usage_poll = time.time()
        try:
            if self.history_start is None:
                res = starlink_grpc.history_stats(300, context=self.ctx)
            else:
                res = starlink_grpc.history_stats(-1, start=self.history_start, context=self.ctx)
            general, usage, power = res[0], res[5], res[6]
            end = general.get("end_counter")
            if self.history_start is not None and end is not None and end < self.history_start:
                self.history_start = None  # dish rebooted; counters reset
                return
            self.history_start = end
            down, up = usage.get("download_usage") or 0, usage.get("upload_usage") or 0
            conn = db()
            conn.execute("INSERT INTO usage(day, down_bytes, up_bytes) VALUES(?,?,?) ON CONFLICT(day) DO UPDATE "
                         "SET down_bytes=down_bytes+excluded.down_bytes, up_bytes=up_bytes+excluded.up_bytes",
                         (today(), down, up))
            conn.commit()
            conn.close()
            if power.get("mean_power") is not None:
                self.power_w = round(power["mean_power"], 1)
        except Exception as e:  # noqa: BLE001
            log(C, f"usage poll failed: {e}")
            self.history_start = None

    def maybe_reboot(self, cfg, d: dict, on_starlink: bool) -> None:
        """Safety net: restart the dish only if it is stuck (on, sky clear, but no service) for 15 min."""
        stuck = (on_starlink and d.get("reachable") and d.get("state") not in ("CONNECTED", None)
                 and not d.get("currently_obstructed") and (d.get("obstructed_pct") or 0) < 20)
        if not stuck:
            self.bad_since = None
            return
        self.bad_since = self.bad_since or time.time()
        if time.time() - self.bad_since > 900 and time.time() - self.last_reboot > 3600:
            log(C, f"dish stuck in {d.get('state')} for 15 min; restarting it")
            try:
                starlink_grpc.reboot(context=self.ctx)
                self.last_reboot = time.time()
                self.bad_since = None
                alert(cfg, "Starlink restarted", f"It was stuck ({d.get('state')}) for 15 min, so the Pi restarted it.",
                      key="dish-reboot", cooldown_s=3600, tags="arrows_counterclockwise", category="info")
            except Exception as e:  # noqa: BLE001
                log(C, f"reboot failed: {e}")


def _r(v, nd):
    try:
        return round(float(v), nd) if nd else round(float(v))
    except (TypeError, ValueError):
        return None


def quality(d: dict) -> str:
    if not d.get("reachable") or d.get("state") != "CONNECTED":
        return "down"
    if (d.get("drop_pct") or 0) > 5 or (d.get("ping_ms") or 0) > 120 or d.get("currently_obstructed"):
        return "weak"
    return "good"


def meters(a, b) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    x = (lon2 - lon1) * math.cos((lat1 + lat2) / 2)
    return 6371000 * math.hypot(x, lat2 - lat1)


# ---------------------------------------------------------------- dashcam USB link
class UsbWatch:
    """Watches whether the car is connected to the Pi's dashcam drive, retries once, and alerts."""

    def __init__(self):
        self.not_attached_since = None
        self.rebound = False
        st = read_json(MON_STATE, {}) or {}
        self.ever_connected = bool(st.get("car_ever_connected"))
        self.connected_this_boot = False
        self.klog_at = 0.0
        self.klog: list[str] = []

    def check(self, cfg, usb: dict, uptime: int) -> dict:
        info = dict(usb)
        connected = usb.get("car_connected")
        if connected:
            self.not_attached_since = None
            if not self.connected_this_boot:
                self.connected_this_boot = True
                st = read_json(MON_STATE, {}) or {}
                st["car_last_connected"] = time.time()
                if not self.ever_connected:
                    self.ever_connected = True
                    st["car_ever_connected"] = True
                    alert(cfg, "Dashcam is recording to the Pi",
                          "The car connected to the Pi's dashcam drive. You can leave the flash drive out now.",
                          key="car-first-connect", cooldown_s=10 * 365 * 86400, category="info")
                write_json(MON_STATE, st)
        elif usb.get("bound"):
            self.not_attached_since = self.not_attached_since or time.time()
            waited = time.time() - self.not_attached_since
            # The car usually connects within seconds. If not, re-offer the drive once.
            if waited > 60 and not self.rebound and uptime > 90:
                self.rebound = True
                log(C, "car hasn't connected to the dashcam drive; re-offering it")
                run([GADGET_SH, "rebind"], timeout=30)
            if waited > 180 and uptime > 240 and self.ever_connected and not self.connected_this_boot:
                alert(cfg, "Car isn't seeing the dashcam drive",
                      "The Pi is on but the car hasn't connected to it. Check the cable is in the Pi's USB0 port.",
                      key="car-not-connected", cooldown_s=6 * 3600, tags="rotating_light")
            elif waited > 240 and uptime > 300 and not self.ever_connected:
                alert(cfg, "Car hasn't connected to the dashcam drive yet",
                      "The Pi is on and offering the drive, but the car isn't connected. The glovebox cable must go "
                      "into the Pi's USB0 port (end of the board, next to the antenna). Keep the flash drive in until then.",
                      key="car-never-connected", cooldown_s=12 * 3600, tags="rotating_light")
        info["low"] = usb_lowlevel(usb.get("udc"))
        if not connected and time.time() - self.klog_at > 60:
            self.klog_at = time.time()
            self.klog = usb_kernel_log()
        info["klog"] = self.klog if not connected else None
        info["hint"] = usb_hint(usb, uptime)
        info["ever_connected"] = self.ever_connected
        info["connected_this_boot"] = self.connected_this_boot
        info["rebind_tried"] = self.rebound
        return info


def usb_hint(usb: dict, uptime: int) -> str | None:
    if usb.get("gadget") == "unsupported" or not usb.get("udcs"):
        return "This Pi isn't offering USB drive mode. Run 'sudo car-atlas doctor' for details."
    if usb.get("usb0_host_overlay"):
        return "USB0 is set to host mode in orangepi-config. Turn off the usb0-host overlay so the car can see the drive."
    if usb.get("car_connected"):
        return None
    if usb.get("state") in ("not attached", None):
        return ("The car isn't connected to the Pi's USB0 port. The cable from the glovebox must go into USB0: "
                "the USB-C port at the end of the board, next to the antenna, farthest from the mini-HDMI.")
    return f"USB link is '{usb.get('state')}'. The car is talking to the Pi but hasn't finished connecting."


# ---------------------------------------------------------------- app commands
def run_commands(cfg, dish: Dish, net: str) -> None:
    """Do what the app asked for (Save recent dashcam, restart Starlink, etc.)."""
    r = cloud(cfg, "GET", "/api/pi/commands", timeout=10)
    for c in (r or {}).get("commands", []):
        cid, kind, args = c.get("id"), c.get("type"), c.get("args") or {}

        def done(ok: bool, msg: str) -> None:
            cloud(cfg, "POST", f"/api/pi/commands/{cid}", {"ok": ok, "result": msg}, timeout=10)

        log(C, f"command {cid}: {kind} {args}")
        if kind == "upload_recent":
            REQ_DIR.mkdir(parents=True, exist_ok=True)
            write_json(REQ_DIR / f"recent_{cid}.json", {"id": cid, "minutes": int(args.get("minutes") or 10)})
        elif kind == "restart_dish":
            if net != "starlink" or not dish.ctx:
                done(False, "The Pi isn't on the Starlink WiFi right now, so it can't reach the dish.")
                continue
            try:
                starlink_grpc.reboot(context=dish.ctx)
                dish.last_reboot = time.time()
                done(True, "Starlink is restarting. Internet is back in about 2 minutes.")
            except Exception as e:  # noqa: BLE001
                done(False, f"The dish didn't take the restart: {str(e)[:120]}")
        elif kind == "update_now":
            run(["systemctl", "start", "--no-block", "car-atlas-update.service"], timeout=15)
            done(True, f"Checking GitHub for updates now (currently on v{version()}).")
        elif kind == "restart_services":
            done(True, "Restarting the uploader and monitor.")
            run(["systemctl", "restart", "car-atlas-uploader.service"], timeout=60)
            run(["systemctl", "restart", "--no-block", "car-atlas-monitor.service"], timeout=15)
        elif kind == "reboot_pi":
            done(True, "The Pi is restarting. Back in about a minute.")
            run(["systemctl", "reboot"], timeout=15)
        elif kind == "test_alert":
            alert(cfg, "Hello from the Pi", "If you see this, the Pi can reach your phone.",
                  key=f"test-{cid}", cooldown_s=1, category="info")
            done(True, "Test alert sent.")
        elif kind == "usb_rebind":
            code, out = run([GADGET_SH, "rebind"], timeout=30)
            time.sleep(3)
            state = usb_info().get("state")
            done(code == 0, f"Re-offered the dashcam drive. USB link is now: {state}.")
        elif kind in ("usb_fix", "usb_fix_undo"):
            done(True, "Applying the USB setting change and restarting the Pi (back in about 2 minutes).")
            run(["systemd-run", "--on-active=3", USB_FIX_SH] + (["undo"] if kind == "usb_fix_undo" else []), timeout=15)
        else:
            done(False, "The Pi doesn't know how to do that yet. Try 'Check for updates'.")


def push_coverage(cfg, conn) -> None:
    st = read_json(CLOUD_STATE, {}) or {}
    since = st.get("coverage_ts", 0)
    rows = conn.execute("SELECT ts, lat, lon, quality, ping_ms, drop_pct FROM coverage WHERE ts > ? ORDER BY ts LIMIT 2000",
                        (since,)).fetchall()
    if not rows:
        return
    pts = [[r[0], r[1], r[2], (r[3] or "g")[0], r[4], r[5]] for r in rows]
    if cloud(cfg, "POST", "/api/pi/coverage", {"points": pts}, timeout=30) is not None:
        st["coverage_ts"] = rows[-1][0]
        write_json(CLOUD_STATE, st)


def prefer_home_wifi(cfg, net: str, state: dict) -> None:
    """NetworkManager won't leave a working network for a better one on its own.
    When the Pi is on Starlink and home WiFi is in range, hop to home WiFi."""
    if net != "starlink" or time.time() - state.get("last_try", 0) < 120:
        return
    home = cfg.get("HOME_SSID")
    code, out = run(["nmcli", "-t", "-f", "SSID,SIGNAL", "dev", "wifi", "list"], timeout=15)
    if code != 0:
        return
    for line in out.splitlines():
        ssid, _, sig = line.rpartition(":")
        if ssid == home and sig.isdigit() and int(sig) >= 35:
            state["last_try"] = time.time()
            log(C, f"home WiFi in range ({sig}); switching off Starlink")
            run(["nmcli", "connection", "up", "home-wifi"], timeout=45)
            return


def version_tuple(v) -> tuple:
    try:
        return tuple(int(x) for x in str(v).strip().split("."))
    except ValueError:
        return (0,)


def note_version_change(cfg) -> None:
    st = read_json(MON_STATE, {}) or {}
    v = version()
    prev = st.get("version")
    if not prev:
        # First run of a versioned build. If the Pi already had Car Atlas before, that was v1.0.
        try:
            conn = db()
            row = conn.execute("SELECT MIN(ts) FROM samples").fetchone()
            conn.close()
            if row and row[0] and time.time() - row[0] > 3600:
                prev = "1.0"
        except Exception:  # noqa: BLE001
            pass
    if prev and prev != v:
        st["updated_from"] = prev
        st["updated_at"] = time.time()
        alert(cfg, f"Pi updated to v{v}", f"The Pi is now running Car Atlas v{v} (was v{prev}).",
              key=f"version-{v}", cooldown_s=365 * 86400, category="info")
    st["version"] = v
    write_json(MON_STATE, st)


# ---------------------------------------------------------------- main loop
def main() -> None:
    cfg = load_config()
    dish = Dish()
    health = PiHealth()
    usbw = UsbWatch()
    gps = GPSReader(cfg.get("GPS_DEVICE", "auto"))
    gps.start()
    poll_s = cfg_int(cfg, "DISH_POLL_INTERVAL", 15)
    status_s = cfg_int(cfg, "STATUS_INTERVAL", 60)
    last_status_push = last_coverage_push = 0.0
    last_point = None
    last_point_ts = last_sample_ts = 0.0
    home_state: dict = {}
    last_cloud_status = last_cloud_cov = last_cmd_poll = 0.0
    last_update_kick = time.time() - 600  # give the boot-time update check a head start
    last_location = (read_json(MON_STATE, {}) or {}).get("last_location")
    version_noted = False
    synced, synced_at = False, 0.0
    log(C, f"started v{version()}")
    while True:
        loop_start = time.time()
        try:
            cfg = load_config()
            wifi = wifi_info()
            net = network_kind(cfg, wifi["ssid"])
            prefer_home_wifi(cfg, net, home_state)
            d = dish.poll() if net == "starlink" else dict(dish.last, reachable=False, error="Pi is not on the Starlink WiFi")
            q = quality(d)
            if time.time() - synced_at > 60 or not synced:
                synced, synced_at = clock_synced(), time.time()
            pi = health.get()
            g = gps.snapshot()

            # Where is the car? USB GPS first, then the dish (if Starlink ever brings it back).
            loc = None
            if g.get("fresh"):
                loc = {"lat": g["lat"], "lon": g["lon"], "source": "gps", "at": g["at"],
                       "speed_mph": g.get("speed_mph"), "sats": g.get("sats")}
            elif d.get("location") and d.get("reachable"):
                loc = dict(d["location"], source="starlink", at=time.time(), speed_mph=None)
            if loc:
                if not last_location or meters((last_location["lat"], last_location["lon"]), (loc["lat"], loc["lon"])) > 30 \
                        or time.time() - last_location.get("at", 0) > 600:
                    st = read_json(MON_STATE, {}) or {}
                    st["last_location"] = loc
                    write_json(MON_STATE, st)
                last_location = loc

            conn = db()
            if synced and time.time() - last_sample_ts >= 60:
                conn.execute("INSERT INTO samples VALUES(?,?,?,?,?,?,?,?,?)",
                             (time.time(), (loc or {}).get("lat"), (loc or {}).get("lon"), d.get("state"), d.get("ping_ms"),
                              d.get("drop_pct"), int(bool(d.get("currently_obstructed"))),
                              d.get("down_mbps"), d.get("up_mbps")))
                last_sample_ts = time.time()
            if synced and loc and net == "starlink":
                p = (loc["lat"], loc["lon"])
                moved = last_point is None or meters(last_point, p) > 75
                if moved or (q != "good" and time.time() - last_point_ts > 60):
                    conn.execute("INSERT INTO coverage VALUES(?,?,?,?,?,?)",
                                 (time.time(), p[0], p[1], q, d.get("ping_ms"), d.get("drop_pct")))
                    last_point, last_point_ts = p, time.time()
            conn.commit()

            dish.maybe_reboot(cfg, d, net == "starlink")
            usb = usbw.check(cfg, usb_info(), pi.get("uptime_s") or 0)
            up = read_json(RUN_DIR / "uploader.json", {}) or {}
            u = conn.execute("SELECT down_bytes, up_bytes FROM usage WHERE day=?", (today(),)).fetchone()
            online = internet_up()
            pend = up.get("pending") or {}
            speed = (loc or {}).get("speed_mph")

            status = {
                "version": 2,
                "updated_epoch": time.time(),
                "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "pi": dict(pi, wifi_ssid=wifi["ssid"], wifi_signal=wifi["signal"], network=net, internet=online),
                "starlink": dict(d, quality=q, last_contact_epoch=dish.last_ok or None,
                                 location_supported=dish.location_supported,
                                 usage_today_mb={"down": round((u[0] if u else 0) / 1e6),
                                                 "up": round((u[1] if u else 0) / 1e6)}),
                "link": {"pi_on_starlink_wifi": net == "starlink",
                         "pi_talking_to_dish": bool(d.get("reachable")),
                         "last_contact_epoch": dish.last_ok or None},
                "location": loc or (dict(last_location, stale=True) if last_location else None),
                "gps": {"device": g.get("device"), "fix": bool(g.get("fresh")), "sats": g.get("sats"),
                        "error": g.get("error") if not g.get("device") else None},
                "motion": {"driving": bool(speed and speed >= 3), "speed_mph": speed} if loc else None,
                "teslacam": {
                    "gadget": usb.get("gadget"),
                    "detail": usb.get("detail"),
                    "usb_link": usb.get("state"),
                    "usb": usb,
                    "image": up.get("image"),
                    "pending": {"dashcam": (pend.get("dashcam") or 0) + (pend.get("encrypted") or 0),
                                "sentry": pend.get("sentry") or 0} if up.get("pending") else None,
                    "uploading": up.get("uploading"),
                    "last_upload": up.get("last_upload"),
                    "last_error": up.get("last_error"),
                    "waiting_for": up.get("waiting_for"),
                    "uploaded_total": up.get("uploaded_total"),
                    "starlink_uploaded_today_mb": up.get("starlink_uploaded_today_mb"),
                    "last_recent_request": up.get("last_recent_request"),
                    "last_cleanup": up.get("last_cleanup"),
                },
                "drive_setup": drive_ready(),
                "cloud": cloud_ready(cfg),
                "alerts_recent": (read_json(STATE_DIR / "alerts_recent.json", []) or [])[:8],
            }
            write_json(STATUS_LOCAL, status)

            # ---- alerts ----
            if not version_noted and online:
                version_noted = True
                note_version_change(cfg)
            if usb.get("gadget") == "unsupported" and (pi.get("uptime_s") or 0) > 90:
                alert(cfg, "Dashcam NOT recording to the Pi",
                      "This Pi isn't offering USB drive mode. Keep a flash drive in the car and check the app.",
                      key="gadget-unsupported", cooldown_s=12 * 3600, tags="rotating_light")
            if usb.get("gadget") == "error" and (pi.get("uptime_s") or 0) > 90:
                alert(cfg, "Dashcam drive problem", f"The Pi couldn't set up the dashcam drive: {usb.get('detail')}. "
                      "Keep a flash drive in the car and run 'sudo car-atlas doctor'.",
                      key="gadget-error", cooldown_s=12 * 3600, tags="rotating_light")
            if (pi.get("cpu_temp_c") or 0) >= cfg_int(cfg, "PI_TEMP_ALERT_C", 80):
                alert(cfg, "Pi running hot", f"{pi['cpu_temp_c']} C in the glovebox.", key="hot",
                      cooldown_s=2 * 3600, tags="fire")
            img = (up.get("image") or {})
            if (img.get("used_pct") or 0) >= 85:
                alert(cfg, "Dashcam drive almost full", f"{img.get('used_pct')}% used. Old clips already in Drive get "
                      "cleared automatically at home.", key="img-full", cooldown_s=24 * 3600, tags="warning")
            if net == "starlink" and dish.last_ok and time.time() - dish.last_ok > 300:
                alert(cfg, "Pi lost contact with Starlink", "On the Starlink WiFi but the dish isn't answering.",
                      key="dish-lost", cooldown_s=3600, tags="satellite")

            # ---- report to car.etjarvis.com and pick up commands from the app ----
            if online and cloud_ready(cfg):
                if time.time() - last_cloud_status >= 30:
                    resp = cloud(cfg, "POST", "/api/pi/status", status, timeout=10)
                    if resp is not None:
                        last_cloud_status = time.time()
                        if resp.get("commands_waiting"):
                            last_cmd_poll = 0.0
                        # The app knows a newer version exists: pull it now instead of waiting for the timer.
                        newer = resp.get("latest_version")
                        if newer and version_tuple(newer) > version_tuple(version()) \
                                and time.time() - last_update_kick > 900:
                            last_update_kick = time.time()
                            log(C, f"v{newer} is available (running v{version()}); updating now")
                            run(["systemctl", "start", "--no-block", "car-atlas-update.service"], timeout=15)
                if time.time() - last_cmd_poll >= 30:
                    last_cmd_poll = time.time()
                    run_commands(cfg, dish, net)
                if time.time() - last_cloud_cov >= 120:
                    last_cloud_cov = time.time()
                    push_coverage(cfg, conn)

            # ---- backup status file in Google Drive ----
            if online and drive_ready() and time.time() - last_status_push >= max(status_s, 120):
                tmp = RUN_DIR / "status.txt"
                tmp.write_text(json.dumps(status, default=str))
                code, out = rclone(["copyto", str(tmp), drive_remote(cfg["DRIVE_STATUS_ID"], "status.txt")], timeout=90)
                if code == 0:
                    last_status_push = time.time()
                else:
                    log(C, f"status push failed: {out[-200:]}")
            if online and drive_ready() and time.time() - last_coverage_push >= 1800:
                cutoff = time.time() - 30 * 86400
                rows = conn.execute("SELECT ts, lat, lon, quality, ping_ms, drop_pct FROM coverage WHERE ts>? "
                                    "ORDER BY ts", (cutoff,)).fetchall()
                pts = [[int(r[0]), r[1], r[2], r[3][0], r[4], r[5]] for r in rows]
                tmp = RUN_DIR / "coverage.txt"
                tmp.write_text(json.dumps({"updated_epoch": time.time(), "fields": ["ts", "lat", "lon", "q", "ping", "drop"],
                                           "points": pts}))
                code, _ = rclone(["copyto", str(tmp), drive_remote(cfg["DRIVE_STATUS_ID"], "coverage.txt")], timeout=120)
                if code == 0:
                    last_coverage_push = time.time()
            conn.execute("DELETE FROM samples WHERE ts < ?", (time.time() - 60 * 86400,))
            conn.commit()
            conn.close()
        except Exception as e:  # noqa: BLE001
            log(C, f"loop error: {e}")
        time.sleep(max(1.0, poll_s - (time.time() - loop_start)))


if __name__ == "__main__":
    main()
