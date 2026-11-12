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
from common import (RUN_DIR, SPEED_LIMITS, STATE_DIR, alert, app_settings, attach_image, cfg_int, cloud,  # noqa: E402
                    cloud_ready, cpu_temp, db, detach_loops, drive_ready, drive_remote, fs_type, internet_up,
                    load_config, log, network_kind, rclone, rclone_progress, read_json, run, today,
                    usb_info, wifi_info, write_json)

C = "uploader"
MNT = RUN_DIR / "teslacam-ro"
STATE_FILE = RUN_DIR / "uploader.json"
SIGS_FILE = STATE_DIR / "pending_sigs.json"
REQ_DIR = STATE_DIR / "requests"


class ReadOnlyView:
    """Opens the dashcam image read-only, fresh each time so we see the car's latest writes."""

    def __init__(self, image: str, mnt: Path | None = None):
        self.image = image
        self.mnt = mnt or MNT
        self.loops: list[str] = []

    def __enter__(self):
        if not os.path.isfile(self.image):
            return None
        part, self.loops = attach_image(self.image, read_only=True)
        if not part:
            return None
        self.mnt.mkdir(parents=True, exist_ok=True)
        fst = fs_type(part) or "vfat"
        self.fst = fst
        opts = "ro,noatime,utf8" if fst == "vfat" else "ro,noatime"
        code, out = run(["mount", "-t", fst, "-o", opts, part, str(self.mnt)])
        if code != 0:  # let the kernel guess
            code, out = run(["mount", "-o", "ro,noatime", part, str(self.mnt)])
        if code != 0:
            log(C, f"mount failed: {out.strip()}")
            detach_loops(self.loops)
            self.loops = []
            return None
        return self.mnt

    def __exit__(self, *exc):
        run(["umount", str(self.mnt)])
        detach_loops(self.loops)
        self.loops = []


def clip_roots(cam: Path) -> list[tuple[Path, bool]]:
    """Folders the car writes clips into. Tesla software 2026.20+ encrypts clips by default and puts
    them under TeslaCam/EncryptedClips/ (SavedClips, SentryClips, RecentClips inside it)."""
    return [(cam, False), (cam / "EncryptedClips", True)]


def recent_dirs(cam: Path) -> list[Path]:
    return [root / "RecentClips" for root, _ in clip_roots(cam) if (root / "RecentClips").is_dir()]


def is_png(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(8) == b"\x89PNG\r\n\x1a\n"
    except OSError:
        return False


def drive_tree(mnt: Path) -> list:
    """A short look at what the car has put on the drive (for the health check)."""
    out = []
    try:
        tops = sorted(mnt.iterdir())
    except OSError:
        return out
    for top in tops[:12]:
        if not top.is_dir():
            out.append(f"{top.name} (file)")
            continue
        try:
            subs = sorted(top.iterdir())
        except OSError:
            continue
        for sub in subs[:12]:
            if not sub.is_dir():
                continue
            try:
                kids = sorted(sub.iterdir())
            except OSError:
                continue
            files = [k for k in kids if k.is_file()]
            dirs = [k for k in kids if k.is_dir()]
            names = ", ".join(k.name for k in kids[-2:])
            out.append(f"{top.name}/{sub.name}: {len(dirs)} folders, {len(files)} files; newest: {names[:110]}")
            if dirs:
                d = dirs[-1]
                try:
                    inner = sorted(d.iterdir())
                    mb = sum(f.stat().st_size for f in inner if f.is_file()) / 1e6
                    out.append(f"   {d.name}: {len(inner)} items, {mb:.0f} MB; e.g. {', '.join(i.name for i in inner[-2:])[:110]}")
                except OSError:
                    pass
    return out[:30]


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


def budget_left_bytes(conn, cfg, settings: dict | None = None) -> int:
    cap_mb = (settings or {}).get("starlink_cap_mb") or cfg_int(cfg, "STARLINK_DAILY_UPLOAD_CAP_MB", 5000)
    cap = int(cap_mb) * 1_000_000
    row = conn.execute("SELECT starlink_bytes FROM upload_budget WHERE day=?", (today(),)).fetchone()
    return cap - (row[0] if row else 0)


def add_budget(conn, nbytes: int) -> None:
    conn.execute("INSERT INTO upload_budget(day, starlink_bytes) VALUES(?, ?) "
                 "ON CONFLICT(day) DO UPDATE SET starlink_bytes = starlink_bytes + excluded.starlink_bytes",
                 (today(), nbytes))
    conn.commit()


def upload_folder(cfg, src: Path, dest_folder_id: str, name: str, bwlimit: str, st: dict | None = None) -> tuple[bool, str]:
    def progress(p: dict) -> None:
        up = (st or {}).get("uploading")
        if not up or not p.get("total"):
            return
        up.update({"pct": round(100 * p["bytes"] / p["total"]), "eta_s": p.get("eta"),
                   "kbps": round((p.get("speed") or 0) * 8 / 1000), "at": time.time()})
        write_json(STATE_FILE, st)

    code, out = rclone_progress(["copy", str(src), drive_remote(dest_folder_id, name),
                                 "--transfers", "2", "--checkers", "4"],
                                timeout=6 * 3600, bwlimit=bwlimit, on_stats=progress)
    return code == 0, out[-400:]


CAMERAS = ("front", "back", "left_repeater", "right_repeater", "left_pillar", "right_pillar")


def drive_file_links(dest_folder_id: str, name: str) -> list | None:
    """Drive IDs of each camera's video in an uploaded clip folder, so the app can open one directly.
    Returns [[minute_stamp, camera, drive_id], ...] newest minute first (capped)."""
    code, out = rclone(["lsjson", "-R", "--files-only", "--no-modtime", "--no-mimetype",
                        drive_remote(dest_folder_id, name)], timeout=120)
    if code != 0:
        return None
    try:
        items = json.loads(out[out.index("["):])
    except (ValueError, json.JSONDecodeError):
        return None
    rows = []
    for it in items:
        n, fid = it.get("Name") or "", it.get("ID")
        if not fid or not n.lower().endswith(".mp4") or len(n) < 24:
            continue
        stamp, cam = n[:19], n[20:-4]
        rows.append([stamp, cam if cam in CAMERAS else cam[:20], fid])
    rows.sort(key=lambda r: (r[0], CAMERAS.index(r[1]) if r[1] in CAMERAS else 9), reverse=False)
    rows.sort(key=lambda r: r[0], reverse=True)
    return rows[:72] or None


def drive_about(st: dict) -> None:
    """How full Google Drive is (checked every 30 min)."""
    if time.time() - (st.get("drive") or {}).get("at", 0) < 1800:
        return
    code, out = rclone(["about", "gdrive:", "--json"], timeout=60)
    if code != 0:
        return
    try:
        j = json.loads(out[out.index("{"):])
    except (ValueError, json.JSONDecodeError):
        return
    gb = lambda v: round(v / 1e9, 1) if isinstance(v, (int, float)) else None  # noqa: E731
    st["drive"] = {"at": time.time(), "total_gb": gb(j.get("total")), "used_gb": gb(j.get("used")),
                   "free_gb": gb(j.get("free")), "trash_gb": gb(j.get("trashed"))}


RETENTION_TYPES = ["*.mp4", "*.MP4", "event.json", "thumb.png", "-README_*.txt"]


def apply_retention(cfg, st: dict, days: int) -> None:
    """If turned on in the app: once a day, move car footage older than N days to Drive's trash.

    Safety rails:
    - Only inside the Tesla Footage/Dashcam and Tesla Footage/Sentry folders (by their fixed Drive IDs).
      Nothing else in Google Drive can be reached: not Tesla Footage itself, not Pi Status, not anything outside.
    - Only the file types the car makes (videos, event.json, thumb.png, Tesla's README). Anything else you
      put in those folders is never touched.
    - Age is when the car recorded it. Deleted files go to Drive's trash (Google keeps them 30 more days).
    """
    if not days or days < 7:
        return
    if time.time() - st.get("retention_at", 0) < 20 * 3600:
        return
    targets = [cfg.get("DRIVE_DASHCAM_ID"), cfg.get("DRIVE_SENTRY_ID")]
    blocked = {cfg.get("DRIVE_ROOT_ID"), cfg.get("DRIVE_STATUS_ID"), "", None, "root"}
    if any(t in blocked for t in targets):
        log(C, "retention: folder settings look wrong; not deleting anything")
        return
    include = []
    for pattern in RETENTION_TYPES:
        include += ["--include", pattern]
    removed = 0
    for fid in targets:
        code, out = rclone(["delete", drive_remote(fid), *include, "--min-age", f"{int(days)}d",
                            "--drive-use-trash=true", "-v"], timeout=900)
        if code != 0:
            log(C, f"retention: delete failed: {out[-200:]}")
            return
        removed += out.count("Deleted")
        # Remove clip folders that are now empty (folders that still hold anything are left alone).
        rclone(["rmdirs", drive_remote(fid), "--leave-root"], timeout=900)
    st["retention_at"] = time.time()
    st["retention"] = {"at": time.time(), "days": int(days), "files_removed": removed}
    if removed:
        log(C, f"retention: moved {removed} files older than {days} days to Drive trash")


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
            "drive_id": drive_folder_id(dest_id, name),
            "encrypted": bool(src is not None and "EncryptedClips" in src.parts)}
    try:
        info["files"] = drive_file_links(dest_id, name)
    except Exception as e:  # noqa: BLE001 - links are a nicety
        log(C, f"file links failed: {e}")
    if src is not None:
        ev = read_json(src / "event.json", {}) or {}
        info.update({"reason": ev.get("reason"), "city": ev.get("city"), "event_ts": ev.get("timestamp"),
                     "camera": ev.get("camera")})
        for k_src, k_dst in (("est_lat", "lat"), ("est_lon", "lon")):
            try:
                info[k_dst] = float(ev.get(k_src)) if ev.get(k_src) not in (None, "") else None
            except (TypeError, ValueError):
                info[k_dst] = None
        thumb = src / "thumb.png"
        try:
            if thumb.is_file() and thumb.stat().st_size < 500_000 and is_png(thumb):
                info["thumb_b64"] = base64.b64encode(thumb.read_bytes()).decode()
                info["thumb_type"] = "image/png"
        except OSError:
            pass
    cloud(cfg, "POST", "/api/pi/clip", info, timeout=60)


def upload_recent(cfg, mnt: Path, minutes: int, bwlimit: str, net: str, st: dict | None = None) -> dict:
    """Upload the last N minutes of RecentClips into Dashcam/Recent_<time>."""
    dirs = recent_dirs(mnt / "TeslaCam")
    # Newest footage wins: with encryption on, the car writes RecentClips inside EncryptedClips.
    dirs.sort(key=lambda d: max((f.stat().st_mtime for f in d.glob("*.mp4")), default=0), reverse=True)
    recent = dirs[0] if dirs else mnt / "TeslaCam" / "RecentClips"
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
    if st is not None:
        st["uploading"] = {"kind": "requested", "folder": dest, "mb": round(size / 1e6), "since": time.time(),
                           "pct": 0, "eta_s": None, "kbps": None}
        write_json(STATE_FILE, st)

    def progress(p: dict) -> None:
        up = (st or {}).get("uploading")
        if up and p.get("total"):
            up.update({"pct": round(100 * p["bytes"] / p["total"]), "eta_s": p.get("eta"),
                       "kbps": round((p.get("speed") or 0) * 8 / 1000), "at": time.time()})
            write_json(STATE_FILE, st)

    code, out = rclone_progress(["copy", str(recent), drive_remote(cfg["DRIVE_DASHCAM_ID"], dest),
                                 "--files-from", str(list_path), "--transfers", "2"],
                                timeout=4 * 3600, bwlimit=bwlimit, on_stats=progress)
    if st is not None:
        st["uploading"] = None
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
        try:
            age = time.time() - req.stat().st_mtime
        except OSError:
            continue
        if age > 6 * 3600:
            # Too old: the footage it asked for has rolled off, and a stale request must never block new clips.
            log(C, f"dropping old recent-footage request {req.name} ({age / 3600:.0f} h old)")
            if r.get("id"):
                cloud(cfg, "POST", f"/api/pi/commands/{r['id']}", {"ok": False, "result": "Expired before the Pi could do it."})
            req.unlink(missing_ok=True)
            continue
        minutes = max(1, min(60, int(r.get("minutes") or 10)))
        req.unlink(missing_ok=True)
        res = upload_recent(cfg, mnt, minutes, bwlimit, net, st)
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
    # Delete the request first, so a slow or interrupted upload can never repeat forever.
    rclone(["deletefile", drive_remote(status_id, req_name)], timeout=60)
    st["last_recent_request"] = upload_recent(cfg, mnt, minutes, bwlimit, net, st)


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
    present = set(st.get("present") or [])
    rows = [r for r in conn.execute("SELECT kind, folder FROM uploads WHERE uploaded_at < ?", (cutoff,)).fetchall()
            if f"{r[0]}/{r[1]}" in present]
    if not rows:
        return            # nothing uploaded is still taking space; the car manages its own rolling footage
    gadget_sh = str(Path(__file__).resolve().parent.parent / "scripts" / "teslacam-gadget.sh")
    log(C, f"drive {used}% full; cleaning up {len(rows)} uploaded folders")
    run([gadget_sh, "stop"], timeout=30)
    removed, loops = 0, []
    try:
        part, loops = attach_image(cfg["TESLACAM_IMAGE"], read_only=False)
        if not part:
            raise RuntimeError("could not attach the drive image")
        fst = fs_type(part) or "vfat"
        run(["fsck.exfat" if fst == "exfat" else "fsck.vfat", "-y" if fst == "exfat" else "-a", part], timeout=300)
        rw = RUN_DIR / "teslacam-rw"
        rw.mkdir(parents=True, exist_ok=True)
        code, out = run(["mount", "-t", fst, "-o", "rw,noatime", part, str(rw)])
        if code != 0:
            raise RuntimeError(out)
        try:
            for kind, folder in rows:
                sub = {"dashcam": "SavedClips", "sentry": "SentryClips"}.get(kind, "SavedClips")
                for root in (rw / "TeslaCam", rw / "TeslaCam" / "EncryptedClips"):
                    target = root / sub / folder
                    if not (target.is_dir() and target.parent.name == sub):
                        continue
                    run(["rm", "-rf", "--one-file-system", str(target)], timeout=120)
                    removed += 1
            run(["sync"], timeout=60)
        finally:
            run(["umount", str(rw)], timeout=60)
    except Exception as e:  # noqa: BLE001
        log(C, f"cleanup error: {e}")
    finally:
        detach_loops(loops)
        run([gadget_sh, "start"], timeout=120)
    st["last_cleanup"] = {"at": time.time(), "removed": removed, "was_used_pct": used}
    log(C, f"cleanup removed {removed} folders; drive re-attached")


def cycle(cfg, conn, st: dict, pending: dict) -> None:
    usb = usb_info()
    st["gadget"] = usb.get("gadget")
    st["gadget_detail"] = usb.get("detail")
    st["usb_link"] = usb.get("state")

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
        if time.time() - st.get("tree_at", 0) > 300:
            st["tree_at"] = time.time()
            st["tree"] = drive_tree(mnt)
        queue = []
        seen = set()
        counts = {"dashcam": 0, "sentry": 0, "encrypted": 0}
        pending_bytes = clip_bytes = 0
        st["encrypted_seen"] = False
        for root, encrypted in clip_roots(cam):
            for sub, dest_id, kind in kinds:
                base = root / sub
                if not base.is_dir():
                    continue
                for folder in sorted(p for p in base.iterdir() if p.is_dir()):
                    sig, size = folder_sig(folder)
                    if not sig:
                        continue
                    clip_bytes += size
                    if encrypted:
                        st["encrypted_seen"] = True
                    key = f"{kind}/{folder.name}"
                    seen.add(key)
                    row = conn.execute("SELECT sig FROM uploads WHERE kind=? AND folder=?",
                                       (kind, folder.name)).fetchone()
                    if row and row[0] == sig:
                        continue
                    counts[kind] += 1
                    if encrypted:
                        counts["encrypted"] += 1
                    pending_bytes += size
                    # Only upload once the car has stopped writing to this folder
                    if pending.get(key) == sig:
                        queue.append((kind, folder, dest_id, sig, size))
                    pending[key] = sig
        st["image"]["clips_gb"] = round(clip_bytes / 1e9, 1)
        st["present"] = sorted(seen)
        for stale in [k for k in pending if k not in seen]:
            pending.pop(stale, None)
        st["pending"] = counts
        st["pending_mb"] = round(pending_bytes / 1e6)
        st["recent_folder_present"] = bool(recent_dirs(cam))
        st["updated"] = time.time()
        write_json(STATE_FILE, st)

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
        S = app_settings()
        st["settings_rev"] = S.get("rev")
        if net == "starlink":
            bwlimit = SPEED_LIMITS.get(str(S.get("starlink_speed")), cfg.get("UPLOAD_LIMIT_STARLINK", "375k"))
        else:
            bwlimit = cfg.get("UPLOAD_LIMIT_OTHER", "0")
        st["bwlimit"] = bwlimit

        try:
            drive_about(st)
            apply_retention(cfg, st, int(S.get("retention_days") or 0))
        except Exception as e:  # noqa: BLE001
            log(C, f"drive check failed: {e}")
        drive_free = (st.get("drive") or {}).get("free_gb")
        if drive_free is not None and drive_free < 5:
            alert(cfg, "Google Drive is almost full",
                  f"Only {drive_free} GB left in Google Drive. Clips stop uploading when it runs out.",
                  key="drive-low", cooldown_s=24 * 3600, tags="warning")

        # Something you asked for in the app always goes, even when automatic uploads are held.
        try:
            handle_recent_requests(cfg, mnt, bwlimit, net, st)
        except Exception as e:  # noqa: BLE001
            log(C, f"recent request failed: {e}")

        # Reasons to hold automatic uploads for now
        temp = cpu_temp()
        if S.get("heat_protect") and temp is not None:
            if temp >= cfg_int(cfg, "PI_HOT_PAUSE_C", 84):
                st["hot"] = True
            elif temp <= cfg_int(cfg, "PI_HOT_RESUME_C", 78):
                st["hot"] = False
        else:
            st["hot"] = False
        hold = None
        if S.get("uploads_paused"):
            hold = "you (uploads are paused in the app)"
        elif st.get("hot"):
            hold = "the Pi to cool down"
        elif drive_free is not None and drive_free < 2:
            hold = "space in Google Drive (it's full)"
        if hold:
            if queue:
                st["waiting_for"] = hold
            return

        for kind, folder, dest_id, sig, size in queue:
            if net == "starlink":
                if kind == "sentry" and (not S.get("sentry_on_starlink") or cfg.get("UPLOAD_SENTRY_ON_STARLINK", "1") != "1"):
                    st["waiting_for"] = "home WiFi (Sentry uploads over Starlink are off)"
                    continue
                if kind != "sentry" and not S.get("uploads_on_starlink"):
                    st["waiting_for"] = "home WiFi (Starlink uploads are off)"
                    continue
                if S.get("plan_protect") and (S.get("plan_pct") or 0) >= 90:
                    st["waiting_for"] = "home WiFi (this month's Starlink data is almost used up)"
                    continue
                if size > budget_left_bytes(conn, cfg, S):
                    st["waiting_for"] = "home WiFi (today's Starlink upload limit is reached)"
                    alert(cfg, "Upload limit reached",
                          "Today's Starlink upload limit is used up. The rest uploads on home WiFi.",
                          key="cap-" + today(), cooldown_s=86400, tags="warning", category="info")
                    continue
            log(C, f"uploading {kind} {folder.name} ({size/1e6:.0f} MB) over {net}")
            st["uploading"] = {"kind": kind, "folder": folder.name, "mb": round(size / 1e6), "since": time.time(),
                               "pct": 0, "eta_s": None, "kbps": None}
            write_json(STATE_FILE, st)
            ok, detail = upload_folder(cfg, folder, dest_id, folder.name, bwlimit, st)
            st["uploading"] = None
            if ok:
                conn.execute("INSERT OR REPLACE INTO uploads VALUES(?,?,?,?,?,?)",
                             (kind, folder.name, sig, size, time.time(), net))
                conn.commit()
                if net == "starlink":
                    add_budget(conn, size)
                st["last_upload"] = {"kind": kind, "folder": folder.name, "mb": round(size / 1e6), "at": time.time()}
                st["last_error"] = None
                for ck in (kind, "encrypted") if "EncryptedClips" in folder.parts else (kind,):
                    if st.get("pending", {}).get(ck):
                        st["pending"][ck] -= 1
                st["pending_mb"] = max(0, (st.get("pending_mb") or 0) - round(size / 1e6))
                post_clip(cfg, "sentry" if kind == "sentry" else "dashcam", folder, dest_id, folder.name, size, net)
                label = "Sentry event" if kind == "sentry" else "Dashcam clip"
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


def scan_report() -> str:
    """Everything the Pi can see on the car's drive, and what it thinks of each clip folder."""
    cfg = load_config()
    conn = db()
    out = []
    view = ReadOnlyView(cfg["TESLACAM_IMAGE"], RUN_DIR / "teslacam-scan")
    with view as mnt:
        if mnt is None:
            return "Couldn't open the dashcam drive image."
        out.append(f"Filesystem: {getattr(view, 'fst', '?')}   {image_usage(mnt)}")
        for root, dirs, files in os.walk(mnt):
            rel = os.path.relpath(root, mnt)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth > 4:
                continue
            size = 0
            for f in files:
                try:
                    size += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
            if "RecentClips" in rel.split(os.sep):
                if os.path.basename(root) == "RecentClips":
                    out.append(f"{rel}/  ({len(files)} files, {size/1e6:.0f} MB, rolling recording)")
                dirs[:] = []
                continue
            show = ", ".join(sorted(files)[:4]) + (" ..." if len(files) > 4 else "")
            out.append(f"{rel}/  {len(dirs)} folders, {len(files)} files, {size/1e6:.0f} MB  {show}"[:300])
        out.append("")
        out.append("Clip folders the uploader would consider:")
        cam = mnt / "TeslaCam"
        for root, encrypted in clip_roots(cam):
            for sub in ("SavedClips", "SentryClips"):
                base = root / sub
                if not base.is_dir():
                    out.append(f"  (no {base.relative_to(mnt)})")
                    continue
                for folder in sorted(p for p in base.iterdir() if p.is_dir()):
                    sig, size = folder_sig(folder)
                    kind = "dashcam" if sub == "SavedClips" else "sentry"
                    row = conn.execute("SELECT sig, uploaded_at FROM uploads WHERE kind=? AND folder=?", (kind, folder.name)).fetchone()
                    state = "already uploaded" if row and row[0] == sig else ("uploaded, but changed since" if row else "NOT uploaded yet")
                    out.append(f"  {folder.relative_to(mnt)}: {len(sig.split('|')) if sig else 0} files, {size/1e6:.0f} MB -> {state}")
    st = read_json(STATE_FILE, {}) or {}
    out.append("")
    out.append(f"Uploader state: pending={st.get('pending')} waiting_for={st.get('waiting_for')} "
               f"last_error={st.get('last_error')} drive_view={st.get('drive_view')} updated={st.get('updated')}")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        print(scan_report())
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        c = load_config()
        s: dict = {}
        cycle(c, db(), s, {})
        print(s)
    else:
        main()
