"""Watches the Pi and the Starlink, logs coverage, and publishes status to Google Drive
(Tesla Footage/Pi Status/status.txt), which the dashboard reads.
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
from common import (RUN_DIR, SRC_DIR, STATE_DIR, alert, cfg_int, clock_synced, db,  # noqa: E402
                    drive_ready, drive_remote, internet_up, load_config, log, network_kind,
                    rclone, read_json, run, today, wifi_info, write_json)

C = "monitor"
STATUS_LOCAL = STATE_DIR / "status.json"

try:
    import starlink_grpc  # type: ignore
except Exception:  # noqa: BLE001
    starlink_grpc = None


def pi_health() -> dict:
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
    du = shutil.disk_usage("/")
    out["sd_free_gb"] = round(du.free / 1e9, 1)
    code, ts = run(["tailscale", "ip", "-4"], timeout=5)
    out["tailscale_ip"] = ts.strip().splitlines()[0] if code == 0 and ts.strip() else None
    code, sha = run(["git", "-C", str(SRC_DIR.parent), "rev-parse", "--short", "HEAD"], timeout=5)
    out["code_version"] = sha.strip() if code == 0 else None
    svc = {}
    for name in ("car-atlas-teslacam", "car-atlas-uploader", "car-atlas-monitor", "tailscaled"):
        _, s = run(["systemctl", "is-active", name], timeout=5)
        svc[name] = s.strip() or "unknown"
    out["services"] = svc
    out["clock_synced"] = clock_synced()
    return out


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
        }
        try:
            loc = starlink_grpc.location_data(context=self.ctx)
            if loc.get("latitude") is None:
                d["location_allowed"] = False
                d["location"] = None
            else:
                d["location_allowed"] = True
                d["location"] = {"lat": round(loc["latitude"], 5), "lon": round(loc["longitude"], 5)}
        except Exception:  # noqa: BLE001
            d["location_allowed"] = None
            d["location"] = None
        self.poll_usage(d)
        d["power_w"] = self.power_w
        self.last = d
        return d

    def poll_usage(self, d: dict) -> None:
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
                      key="dish-reboot", cooldown_s=3600, tags="arrows_counterclockwise")
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


def main() -> None:
    cfg = load_config()
    dish = Dish()
    poll_s = cfg_int(cfg, "DISH_POLL_INTERVAL", 15)
    status_s = cfg_int(cfg, "STATUS_INTERVAL", 60)
    last_status_push = 0.0
    last_coverage_push = 0.0
    last_point = None
    last_point_ts = 0.0
    last_sample_ts = 0.0
    boot_alerted = False
    home_state: dict = {}
    log(C, "started")
    while True:
        loop_start = time.time()
        try:
            cfg = load_config()
            wifi = wifi_info()
            net = network_kind(cfg, wifi["ssid"])
            prefer_home_wifi(cfg, net, home_state)
            d = dish.poll() if net == "starlink" else dict(dish.last, reachable=False, error="Pi is not on the Starlink WiFi")
            q = quality(d)
            synced = clock_synced()
            conn = db()
            if synced and time.time() - last_sample_ts >= 60:
                loc = d.get("location") or {}
                conn.execute("INSERT INTO samples VALUES(?,?,?,?,?,?,?,?,?)",
                             (time.time(), loc.get("lat"), loc.get("lon"), d.get("state"), d.get("ping_ms"),
                              d.get("drop_pct"), int(bool(d.get("currently_obstructed"))),
                              d.get("down_mbps"), d.get("up_mbps")))
                last_sample_ts = time.time()
            loc = d.get("location")
            if synced and loc and d.get("reachable"):
                p = (loc["lat"], loc["lon"])
                moved = last_point is None or meters(last_point, p) > 75
                if moved or (q != "good" and time.time() - last_point_ts > 60):
                    conn.execute("INSERT INTO coverage VALUES(?,?,?,?,?,?)",
                                 (time.time(), p[0], p[1], q, d.get("ping_ms"), d.get("drop_pct")))
                    last_point, last_point_ts = p, time.time()
            conn.commit()

            pi = pi_health()
            dish.maybe_reboot(cfg, d, net == "starlink")
            up = read_json(RUN_DIR / "uploader.json", {}) or {}
            gadget = read_json(RUN_DIR / "gadget.json", {}) or {}
            u = conn.execute("SELECT down_bytes, up_bytes FROM usage WHERE day=?", (today(),)).fetchone()
            online = internet_up()

            status = {
                "version": 1,
                "updated_epoch": time.time(),
                "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "pi": dict(pi, wifi_ssid=wifi["ssid"], wifi_signal=wifi["signal"], network=net, internet=online),
                "starlink": dict(d, quality=q, last_contact_epoch=dish.last_ok or None,
                                 usage_today_mb={"down": round((u[0] if u else 0) / 1e6),
                                                 "up": round((u[1] if u else 0) / 1e6)}),
                "link": {"pi_on_starlink_wifi": net == "starlink",
                         "pi_talking_to_dish": bool(d.get("reachable")),
                         "last_contact_epoch": dish.last_ok or None},
                "teslacam": {
                    "gadget": gadget.get("gadget", "unknown"),
                    "detail": gadget.get("detail"),
                    "usb_link": up.get("usb_link"),
                    "image": up.get("image"),
                    "pending": up.get("pending"),
                    "uploading": up.get("uploading"),
                    "last_upload": up.get("last_upload"),
                    "last_error": up.get("last_error"),
                    "waiting_for": up.get("waiting_for"),
                    "uploaded_total": up.get("uploaded_total"),
                    "starlink_uploaded_today_mb": up.get("starlink_uploaded_today_mb"),
                    "last_recent_request": up.get("last_recent_request"),
                },
                "drive_setup": drive_ready(),
                "alerts_recent": (read_json(STATE_DIR / "alerts_recent.json", []) or [])[:8],
            }
            write_json(STATUS_LOCAL, status)

            # ---- alerts ----
            if not boot_alerted and pi.get("uptime_s", 0) > 90:
                boot_alerted = True
                g = gadget.get("gadget") or "not running"
                if g == "unsupported":
                    alert(cfg, "Dashcam NOT recording to the Pi",
                          "This Pi can't act as a USB drive yet. Keep a flash drive in the car.",
                          key="gadget-unsupported", cooldown_s=12 * 3600, tags="rotating_light")
                elif g not in ("attached",):
                    alert(cfg, "Dashcam drive problem", f"USB drive mode is '{g}'. Check the dashboard.",
                          key="gadget-bad", cooldown_s=6 * 3600, tags="rotating_light")
            if (pi.get("cpu_temp_c") or 0) >= cfg_int(cfg, "PI_TEMP_ALERT_C", 80):
                alert(cfg, "Pi running hot", f"{pi['cpu_temp_c']} C in the glovebox.", key="hot",
                      cooldown_s=2 * 3600, tags="fire")
            img = (up.get("image") or {})
            if (img.get("used_pct") or 0) >= 85:
                alert(cfg, "Dashcam drive almost full", f"{img.get('used_pct')}% used. Clear old clips from the car's Viewer.",
                      key="img-full", cooldown_s=24 * 3600, tags="warning")
            if net == "starlink" and dish.last_ok and time.time() - dish.last_ok > 300:
                alert(cfg, "Pi lost contact with Starlink", "On the Starlink WiFi but the dish isn't answering.",
                      key="dish-lost", cooldown_s=3600, tags="satellite")
            if d.get("location_allowed") is False:
                alert(cfg, "Coverage map needs location", "Turn on location access for local network in the Starlink app.",
                      key="loc-off", cooldown_s=7 * 86400, tags="world_map")

            # ---- publish to Drive ----
            if online and drive_ready() and time.time() - last_status_push >= status_s:
                tmp = RUN_DIR / "status.txt"
                tmp.write_text(json.dumps(status, default=str))
                code, out = rclone(["copyto", str(tmp), drive_remote(cfg["DRIVE_STATUS_ID"], "status.txt")], timeout=90)
                if code == 0:
                    last_status_push = time.time()
                else:
                    log(C, f"status push failed: {out[-200:]}")
            if online and drive_ready() and time.time() - last_coverage_push >= 600:
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
            # keep the database small
            conn.execute("DELETE FROM samples WHERE ts < ?", (time.time() - 60 * 86400,))
            conn.commit()
            conn.close()
        except Exception as e:  # noqa: BLE001
            log(C, f"loop error: {e}")
        time.sleep(max(1.0, poll_s - (time.time() - loop_start)))


if __name__ == "__main__":
    main()
