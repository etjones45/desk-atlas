"""Uploads saved Dashcam clips and Sentry clips from the car's USB drive to Google Drive.

How it stays safe for the car's recordings:
- The car owns the drive. The Pi only ever opens a READ-ONLY view of it, and never writes or deletes.
- A clip folder is only uploaded after it stops changing between two scans (so the car is done writing it).
- SavedClips (Dashcam) go first. Sentry next. RecentClips (the rolling last hour) are not uploaded
  automatically because that is far too much data; ask for them from the dashboard instead.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (RUN_DIR, STATE_DIR, alert, cfg_int, cloud, cloud_ready, db, drive_ready,  # noqa: E402
                    drive_remote, internet_up, load_config, log, network_kind, rclone, read_json, run,
                    today, wifi_info, write_json)

C = "uploader"
MNT = RUN_DIR / "teslacam-ro"
STATE_FILE = RUN_DIR / "uploader.json"
SIGS_FILE = STATE_DIR / "pending_sigs.json"
REQ_DIR = STATE_DIR / "requests"


class ReadOnlyView:
    """Opens the dashcam image read-only, fresh each time so we see the car's latest writes."""

    def __init__(self, image: str):
        self.image = image
        self.loop = None

    def __enter__(self):
        if not os.path.isfile(self.image):
            return None
        code, out = run(["losetup", "-r", "-P", "-f", "--show", self.image])
        if code != 0:
            log(C, f"losetup failed: {out.strip()}")
            return None
        self.loop = out.strip().splitlines()[-1]
        part = self.loop + "p1"
        for _ in range(10):
            if os.path.exists(part):
                break
            time.sleep(0.3)
        MNT.mkdir(parents=True, exist_ok=True)
        code, out = run(["mount", "-t", "vfat", "-o", "ro,noatime,utf8", part, str(MNT)])
        if code != 0:
            log(C, f"mount failed: {out.strip()}")
            run(["losetup", "-d", self.loop])
            self.loop = None
            return None
        return MNT

    def __exit__(self, *exc):
        run(["umount", str(MNT)])
        if self.loop:
            run(["losetup", "-d", self.loop])


def folder_sig(path: Path) -> tuple[str, int]:
    total, parts = 0, []
    for f in sorted(path.rglob("*")):
        if f.is_file():
            try:
                s = f.stat().st_size
            except OSError:
                continue
            total += s
            parts.append(f"{f.name}:{s}")
    return "|".join(parts), total


def image_usage(mnt: Path) -> dict:
    try:
        st = os.statvfs(mnt)
        size = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        return {"size_gb": round(size / 1e9, 1), "free_gb": round(free / 1e9, 1),
                "used_pct": round(100 * (size - free) / size, 1) if size else None}
    except OSError:
        return {}


def budget_left_bytes(conn, cfg) -> int:
    cap = cfg_int(cfg, "STARLINK_DAILY_UPLOAD_CAP_MB", 5000) * 1_000_000
    row = conn.execute("SELECT starlink_bytes FROM upload_budget WHERE day=?", (today(),)).fetchone()
    return cap - (row[0] if row else 0)


def add_budget(conn, nbytes: int) -> None:
    conn.execute("INSERT INTO upload_budget(day, starlink_bytes) VALUES(?, ?) "
                 "ON CONFLICT(day) DO UPDATE SET starlink_bytes = starlink_bytes + excluded.starlink_bytes",
                 (today(), nbytes))
    conn.commit()


def upload_folder(cfg, src: Path, dest_folder_id: str, name: str, bwlimit: str) -> tuple[bool, str]:
    code, out = rclone(["copy", str(src), drive_remote(dest_folder_id, name),
                        "--transfers", "2", "--checkers", "4"],
                       timeout=6 * 3600, bwlimit=bwlimit)
    return code == 0, out[-400:]


def drive_folder_id(dest_folder_id: str, name: str) -> str | None:
    code, out = rclone(["lsjson", "--stat", drive_remote(dest_folder_id, name)], timeout=60)
    if code != 0:
        return None
    try:
        return json.loads(out[out.index("{"):]).get("ID")
    except (ValueError, json.JSONDecodeError):
        return None


def post_clip(cfg, kind: str, src: Path | None, dest_id: str, name: str, size: int, net: str) -> None:
    """Tell the app about an uploaded clip (with Tesla's thumbnail and event details when present)."""
    if not cloud_ready(cfg):
        return
    info = {"kind": kind, "folder": name, "size_mb": round(size / 1e6, 1), "network": net,
            "drive_id": drive_folder_id(dest_id, name)}
    if src is not None:
        ev = read_json(src / "event.json", {}) or {}
        info.update({"reason": ev.get("reason"), "city": ev.get("city"), "event_ts": ev.get("timestamp")})
        for k_src, k_dst in (("est_lat", "lat"), ("est_lon", "lon")):
            try:
                info[k_dst] = float(ev.get(k_src)) if ev.get(k_src) not in (None, "") else None
            except (TypeError, ValueError):
                info[k_dst] = None
        thumb = src / "thumb.png"
        try:
            if thumb.is_file() and thumb.stat().st_size < 500_000:
                info["thumb_b64"] = base64.b64encode(thumb.read_bytes()).decode()
                info["thumb_type"] = "image/png"
        except OSError:
            pass
    cloud(cfg, "POST", "/api/pi/clip", info, timeout=60)


def upload_recent(cfg, mnt: Path, minutes: int, bwlimit: str, net: str) -> dict:
    """Upload the last N minutes of RecentClips into Dashcam/Recent_<time>."""
    recent = mnt / "TeslaCam" / "RecentClips"
    files = list(recent.rglob("*.mp4")) if recent.is_dir() else []
    # Tesla names files like 2026-11-09_08-15-30-front.mp4 (one per camera per minute)
    stamps = sorted({f.name[:19] for f in files if len(f.name) > 19}, reverse=True)[:minutes]
    chosen = [f for f in files if f.name[:19] in stamps]
    result = {"at": time.time(), "minutes": minutes, "files": len(chosen)}
    if not chosen:
        result.update({"ok": False, "error": "no recent clips on the drive yet"})
        return result
    list_path = RUN_DIR / "recent_list.txt"
    list_path.write_text("\n".join(str(f.relative_to(recent)) for f in chosen))
    dest = f"Recent_{stamps[0]}"
    size = sum(f.stat().st_size for f in chosen)
    code, out = rclone(["copy", str(recent), drive_remote(cfg["DRIVE_DASHCAM_ID"], dest),
                        "--files-from", str(list_path), "--transfers", "2"],
                       timeout=4 * 3600, bwlimit=bwlimit)
    result.update({"ok": code == 0, "folder": dest, "mb": round(size / 1e6), "error": None if code == 0 else out[-300:]})
    if code == 0:
        post_clip(cfg, "requested", None, cfg["DRIVE_DASHCAM_ID"], dest, size, net)
        alert(cfg, "Dashcam uploaded", f"Last {minutes} min of dashcam is in Google Drive ({dest}).",
              key=f"recent-{dest}", cooldown_s=60, tags="movie_camera", category="clip", to_cloud=False,
              click=f"https://drive.google.com/drive/folders/{cfg['DRIVE_DASHCAM_ID']}")
    return result


def handle_recent_requests(cfg, mnt: Path, bwlimit: str, net: str, st: dict) -> None:
    """Requests come from the app (via the Pi's command queue) or from a request file in Drive/Pi Status."""
    REQ_DIR.mkdir(parents=True, exist_ok=True)
    for req in sorted(REQ_DIR.glob("recent_*.json")):
        r = read_json(req, {}) or {}
        minutes = max(1, min(60, int(r.get("minutes") or 10)))
        res = upload_recent(cfg, mnt, minutes, bwlimit, net)
        st["last_recent_request"] = res
        if r.get("id"):
            msg = (f"{res.get('mb', 0)} MB uploaded to Dashcam/{res['folder']}" if res.get("ok")
                   else f"Didn't upload: {res.get('error')}")
            cloud(cfg, "POST", f"/api/pi/commands/{r['id']}", {"ok": bool(res.get("ok")), "result": msg})
        req.unlink(missing_ok=True)

    status_id = cfg["DRIVE_STATUS_ID"]
    code, out = rclone(["lsf", drive_remote(status_id), "--include", "request_recent*.txt"], timeout=60)
    if code != 0 or not out.strip():
        return
    req_name = out.strip().splitlines()[0].strip()
    _, body = rclone(["cat", drive_remote(status_id, req_name)], timeout=60)
    minutes = 10
    for tok in body.replace(",", " ").split():
        if tok.isdigit():
            minutes = max(1, min(60, int(tok)))
            break
    st["last_recent_request"] = upload_recent(cfg, mnt, minutes, bwlimit, net)
    rclone(["deletefile", drive_remote(status_id, req_name)], timeout=60)


def cleanup_if_needed(cfg, conn, st: dict) -> None:
    """Free space on the dashcam drive so the car never stops recording because it's full.

    Only runs at HOME (car parked in the garage), only when the drive is 70%+ full, and only deletes
    clip folders that are already confirmed in Google Drive and are older than 3 days. The drive is
    unplugged from the car for ~10 seconds while this happens, then plugged back in.
    """
    used = (st.get("image") or {}).get("used_pct") or 0
    if st.get("network") != "home" or used < 70:
        return
    if time.time() - (st.get("last_cleanup") or {}).get("at", 0) < 6 * 3600:
        return
    cutoff = time.time() - 3 * 86400
    rows = conn.execute("SELECT kind, folder FROM uploads WHERE uploaded_at < ?", (cutoff,)).fetchall()
    if not rows:
        return
    gadget_sh = str(Path(__file__).resolve().parent.parent / "scripts" / "teslacam-gadget.sh")
    log(C, f"drive {used}% full; cleaning up {len(rows)} uploaded folders")
    run([gadget_sh, "stop"], timeout=30)
    removed, loop = 0, None
    try:
        code, out = run(["losetup", "-P", "-f", "--show", cfg["TESLACAM_IMAGE"]])
        if code != 0:
            raise RuntimeError(out)
        loop = out.strip().splitlines()[-1]
        part = loop + "p1"
        time.sleep(1)
        run(["fsck.vfat", "-a", part], timeout=300)
        rw = RUN_DIR / "teslacam-rw"
        rw.mkdir(parents=True, exist_ok=True)
        code, out = run(["mount", "-t", "vfat", "-o", "rw,noatime", part, str(rw)])
        if code != 0:
            raise RuntimeError(out)
        try:
            for kind, folder in rows:
                sub = "SavedClips" if kind == "dashcam" else "SentryClips"
                target = rw / "TeslaCam" / sub / folder
                if target.is_dir() and target.parent.name == sub:
                    run(["rm", "-rf", "--one-file-system", str(target)], timeout=120)
                    removed += 1
            run(["sync"], timeout=60)
        finally:
            run(["umount", str(rw)], timeout=60)
    except Exception as e:  # noqa: BLE001
        log(C, f"cleanup error: {e}")
    finally:
        if loop:
            run(["losetup", "-d", loop])
        run([gadget_sh, "start"], timeout=120)
    st["last_cleanup"] = {"at": time.time(), "removed": removed, "was_used_pct": used}
    log(C, f"cleanup removed {removed} folders; drive re-attached")


def cycle(cfg, conn, st: dict, pending: dict) -> None:
    gadget = read_json(RUN_DIR / "gadget.json", {}) or {}
    st["gadget"] = gadget.get("gadget", "unknown")
    st["gadget_detail"] = gadget.get("detail")
    udc = gadget.get("udc")
    if udc:
        try:
            st["usb_link"] = Path(f"/sys/class/udc/{udc}/state").read_text().strip()
        except OSError:
            st["usb_link"] = None

    wifi = wifi_info()
    net = network_kind(cfg, wifi["ssid"])
    st["network"] = net
    online = internet_up()
    st["internet"] = online

    with ReadOnlyView(cfg["TESLACAM_IMAGE"]) as mnt:
        if mnt is None:
            st["drive_view"] = "unavailable"
            return
        st["drive_view"] = "ok"
        st["image"] = image_usage(mnt)
        cam = mnt / "TeslaCam"
        kinds = [("SavedClips", cfg["DRIVE_DASHCAM_ID"], "dashcam"),
                 ("SentryClips", cfg["DRIVE_SENTRY_ID"], "sentry")]
        queue = []
        seen = set()
        counts = {"dashcam": 0, "sentry": 0}
        for sub, dest_id, kind in kinds:
            base = cam / sub
            if not base.is_dir():
                continue
            for folder in sorted(p for p in base.iterdir() if p.is_dir()):
                sig, size = folder_sig(folder)
                if not sig:
                    continue
                key = f"{kind}/{folder.name}"
                seen.add(key)
                row = conn.execute("SELECT sig FROM uploads WHERE kind=? AND folder=?",
                                   (kind, folder.name)).fetchone()
                if row and row[0] == sig:
                    continue
                counts[kind] += 1
                # Only upload once the car has stopped writing to this folder
                if pending.get(key) == sig:
                    queue.append((kind, folder, dest_id, sig, size))
                pending[key] = sig
        for stale in [k for k in pending if k not in seen]:
            pending.pop(stale, None)
        st["pending"] = counts
        st["recent_folder_present"] = (cam / "RecentClips").is_dir()

        if not online or not drive_ready():
            st["waiting_for"] = "internet" if not online else "google drive setup"
            if online and not drive_ready():
                for req in REQ_DIR.glob("recent_*.json"):
                    r = read_json(req, {}) or {}
                    if r.get("id"):
                        cloud(cfg, "POST", f"/api/pi/commands/{r['id']}",
                              {"ok": False, "result": "Google Drive isn't connected on the Pi yet (run: sudo car-atlas drive-setup)"})
                    req.unlink(missing_ok=True)
            return
        st["waiting_for"] = None
        bwlimit = cfg.get("UPLOAD_LIMIT_STARLINK", "375k") if net == "starlink" else cfg.get("UPLOAD_LIMIT_OTHER", "0")

        try:
            handle_recent_requests(cfg, mnt, bwlimit, net, st)
        except Exception as e:  # noqa: BLE001
            log(C, f"recent request failed: {e}")

        for kind, folder, dest_id, sig, size in queue:
            if net == "starlink":
                if kind == "sentry" and cfg.get("UPLOAD_SENTRY_ON_STARLINK", "1") != "1":
                    continue
                if size > budget_left_bytes(conn, cfg):
                    st["waiting_for"] = "home wifi (today's Starlink upload cap reached)"
                    alert(cfg, "Upload cap reached",
                          "Today's Starlink upload limit is used up. The rest uploads on home WiFi.",
                          key="cap-" + today(), cooldown_s=86400, tags="warning", category="info")
                    continue
            log(C, f"uploading {kind} {folder.name} ({size/1e6:.0f} MB) over {net}")
            st["uploading"] = {"kind": kind, "folder": folder.name, "mb": round(size / 1e6), "since": time.time()}
            write_json(STATE_FILE, st)
            ok, detail = upload_folder(cfg, folder, dest_id, folder.name, bwlimit)
            st["uploading"] = None
            if ok:
                conn.execute("INSERT OR REPLACE INTO uploads VALUES(?,?,?,?,?,?)",
                             (kind, folder.name, sig, size, time.time(), net))
                conn.commit()
                if net == "starlink":
                    add_budget(conn, size)
                st["last_upload"] = {"kind": kind, "folder": folder.name, "mb": round(size / 1e6), "at": time.time()}
                st["last_error"] = None
                post_clip(cfg, kind, folder, dest_id, folder.name, size, net)
                label = "Dashcam clip" if kind == "dashcam" else "Sentry event"
                alert(cfg, f"{label} saved to Drive", f"{folder.name} ({size/1e6:.0f} MB) uploaded.",
                      key=f"up-{kind}-{folder.name}", cooldown_s=10, tags="white_check_mark",
                      category="clip", to_cloud=False,
                      click=f"https://drive.google.com/drive/folders/{dest_id}")
            else:
                st["last_error"] = {"at": time.time(), "folder": folder.name, "detail": detail}
                log(C, f"upload failed: {detail}")
                alert(cfg, "Clip upload failed", f"{folder.name}: will retry automatically.",
                      key="upload-failed", cooldown_s=3 * 3600, tags="warning")
                break


def main() -> None:
    cfg = load_config()
    conn = db()
    st = read_json(STATE_FILE, {}) or {}
    st.pop("uploading", None)
    pending = read_json(SIGS_FILE, {}) or {}
    interval = cfg_int(cfg, "UPLOAD_SCAN_INTERVAL", 60)
    log(C, "started")
    while True:
        try:
            cfg = load_config()
            cycle(cfg, conn, st, pending)
            cleanup_if_needed(cfg, conn, st)
            row = conn.execute("SELECT COUNT(*), COALESCE(SUM(bytes),0) FROM uploads").fetchone()
            st["uploaded_total"] = {"folders": row[0], "gb": round(row[1] / 1e9, 2)}
            b = conn.execute("SELECT starlink_bytes FROM upload_budget WHERE day=?", (today(),)).fetchone()
            st["starlink_uploaded_today_mb"] = round((b[0] if b else 0) / 1e6)
        except Exception as e:  # noqa: BLE001 - never die; systemd would restart anyway
            log(C, f"cycle error: {e}")
            st["last_error"] = {"at": time.time(), "detail": str(e)[:300]}
            run(["umount", str(MNT)])
        st["updated"] = time.time()
        write_json(STATE_FILE, st)
        write_json(SIGS_FILE, pending)
        time.sleep(interval)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        c = load_config()
        s: dict = {}
        cycle(c, db(), s, {})
        print(s)
    else:
        main()
