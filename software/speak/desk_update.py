#!/usr/bin/env python3
"""Desk Atlas phone update: pull upstream, sync into live, restart units, speak.

Never logs ATLAS_SENDER_KEY / XAI_API_KEY / tokens.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

LIVE = Path(os.environ.get("DESK_ATLAS_LIVE", str(Path.home() / "desk-atlas"))).expanduser()
UPSTREAM = Path(
    os.environ.get("DESK_ATLAS_UPSTREAM", str(Path.home() / "desk-atlas-upstream"))
).expanduser()
PULL_BIN = Path(
    os.environ.get("DESK_ATLAS_PULL", str(Path.home() / "bin" / "desk-atlas-pull"))
).expanduser()

# Upstream path -> live relative path (or callable resolver).
# Keep /update in live speak_server: sync speak_server.py only if upstream copy
# already contains desk_update / "/update".
SYNC_MAP: list[tuple[str, str]] = [
    # Prefer Pi speak server; fall back handled in resolve_speak_src()
    ("software/speak/tts_xai.py", "tts_xai.py"),
    ("software/speak/ack_text.py", "ack_text.py"),
    ("software/speak/atlas_webhook.py", "atlas_webhook.py"),
    ("software/speak/desk_state.py", "desk_state.py"),
    ("software/speak/play_audio.py", "play_audio.py"),
    ("software/speak/desk_update.py", "desk_update.py"),
    ("software/speak/post_speak_once.py", "post_speak_once.py"),
    ("software/speak/face.py", "face.py"),  # WhisPlay anim — required for OTA face upgrades
]

EARS_FLAT_CANDIDATES = [
    "software/ears/ears.py",
]

SKIP_NAME_PARTS = {".env", "venv", "__pycache__"}
SKIP_SUFFIXES = {".bak"}


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 120) -> dict[str, Any]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout: {' '.join(cmd[:3])}"}
    except OSError as e:
        return {"ok": False, "error": f"exec failed: {e}"}
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    return {
        "ok": p.returncode == 0,
        "code": p.returncode,
        "stdout": out[-2000:],
        "stderr": err[-2000:],
    }


def pull_upstream() -> dict[str, Any]:
    if PULL_BIN.is_file() and os.access(PULL_BIN, os.X_OK):
        r = _run([str(PULL_BIN)], timeout=180)
        r["via"] = "desk-atlas-pull"
        return r
    if not (UPSTREAM / ".git").is_dir():
        return {"ok": False, "error": "no upstream clone and no pull helper"}
    r1 = _run(["git", "fetch", "--all", "--prune"], cwd=UPSTREAM, timeout=120)
    if not r1.get("ok"):
        r1["via"] = "git-fetch"
        return r1
    r2 = _run(["git", "pull", "--ff-only"], cwd=UPSTREAM, timeout=120)
    r2["via"] = "git-pull-ff-only"
    if r2.get("ok"):
        tip = _run(["git", "log", "-1", "--oneline"], cwd=UPSTREAM, timeout=30)
        r2["tip"] = (tip.get("stdout") or "").strip()
    return r2


def _upstream_has_update_handler(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return ("/update" in text) and ("desk_update" in text or "run_update" in text)


def resolve_speak_src() -> Path | None:
    candidates = [
        UPSTREAM / "software/speak/speak_server.pi.py",
        UPSTREAM / "software/speak/speak_server.py",
        UPSTREAM / "software/speak/speak_server.laptop.py",
    ]
    for c in candidates:
        if c.is_file() and _upstream_has_update_handler(c):
            return c
    return None


def _should_skip(rel: Path) -> bool:
    parts = set(rel.parts)
    if parts & SKIP_NAME_PARTS:
        return True
    if rel.name == "face.py":
        # Never delete; only overwrite if upstream provides it (caller checks exists).
        pass
    if rel.suffix in SKIP_SUFFIXES or rel.name.endswith(".bak"):
        return True
    return False


def _copy_file(src: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return str(dest.relative_to(LIVE))


def sync_mapped() -> dict[str, Any]:
    if not UPSTREAM.is_dir():
        return {"ok": False, "error": "upstream missing", "copied": []}
    if not LIVE.is_dir():
        return {"ok": False, "error": "live missing", "copied": []}

    copied: list[str] = []
    skipped: list[str] = []

    for up_rel, live_rel in SYNC_MAP:
        src = UPSTREAM / up_rel
        if not src.is_file():
            skipped.append(up_rel)
            continue
        dest = LIVE / live_rel
        if live_rel == "face.py" and not src.is_file():
            skipped.append(up_rel)
            continue
        copied.append(_copy_file(src, dest))

    speak_src = resolve_speak_src()
    if speak_src is not None:
        copied.append(_copy_file(speak_src, LIVE / "speak_server.py"))
    else:
        skipped.append("speak_server (upstream lacks /update; kept live)")

    # ears: NEVER copy CLI-only software/ears/ears.py over live listen ears.
    # Only sync ears.py when upstream file itself supports --listen.
    for up_rel in EARS_FLAT_CANDIDATES:
        src = UPSTREAM / up_rel
        if not src.is_file():
            continue
        try:
            ears_txt = src.read_text(encoding="utf-8", errors="replace")
        except OSError:
            skipped.append(f"{up_rel} (unreadable)")
            break
        if "--listen" not in ears_txt:
            skipped.append(
                f"{up_rel} (CLI-only; kept live listen ears.py — refuses overwrite)"
            )
            # Still allow helper sync (stt/record/webhook) without touching ears.py
            ears_dir = UPSTREAM / "software/ears"
            if ears_dir.is_dir():
                for helper in ("stt_xai.py", "webhook.py", "record.py", "__init__.py"):
                    h = ears_dir / helper
                    if h.is_file():
                        copied.append(_copy_file(h, LIVE / helper))
                        if (LIVE / "ears").is_dir() or helper == "__init__.py":
                            copied.append(_copy_file(h, LIVE / "ears" / helper))
            break
        copied.append(_copy_file(src, LIVE / "ears.py"))
        ears_dir = UPSTREAM / "software/ears"
        if ears_dir.is_dir():
            for helper in ("stt_xai.py", "webhook.py", "record.py", "__init__.py"):
                h = ears_dir / helper
                if h.is_file():
                    copied.append(_copy_file(h, LIVE / helper))
                    if (LIVE / "ears").is_dir() or helper == "__init__.py":
                        copied.append(_copy_file(h, LIVE / "ears" / helper))
        break
    else:
        skipped.append("ears.py")

    # Always sync face.py (critical UI; also guards stale in-memory SYNC_MAP)
    face_src = UPSTREAM / "software" / "speak" / "face.py"
    if face_src.is_file():
        copied.append(_copy_file(face_src, LIVE / "face.py"))
    elif (LIVE / "face.py").is_file():
        skipped.append("software/speak/face.py (missing upstream; kept live)")
    else:
        skipped.append("software/speak/face.py (missing)")

    # Never touch .env / venv
    env_ok = (LIVE / ".env").is_file()
    return {
        "ok": True,
        "copied": copied,
        "skipped": skipped,
        "env_present": env_ok,
    }


def restart_services() -> dict[str, Any]:
    """Bounce desk units. Prefer systemctl; fall back to pkill (Restart=always)."""
    import time

    units = ["desk-atlas.service", "desk-atlas-ears.service"]
    r = _run(["sudo", "-n", "systemctl", "restart", *units], timeout=60)
    if r.get("ok"):
        r["method"] = "sudo-systemctl"
        return r
    r2 = _run(["systemctl", "--user", "restart", *units], timeout=60)
    if r2.get("ok"):
        r2["method"] = "systemctl-user"
        return r2

    # No sudoers: kill processes; systemd Restart=always brings them back.
    _run(["pkill", "-f", "/home/orangepi/desk-atlas/speak_server.py"], timeout=15)
    _run(["pkill", "-f", "speak_server.py"], timeout=15)
    _run(["pkill", "-f", "/home/orangepi/desk-atlas/ears.py"], timeout=15)
    time.sleep(3.0)
    speak_up = _run(["pgrep", "-f", "speak_server.py"], timeout=10)
    ears_up = _run(["pgrep", "-f", "ears.py --listen"], timeout=10)
    ok = bool(speak_up.get("ok"))  # pgrep ok => found
    return {
        "ok": ok,
        "method": "pkill-Restart=always",
        "speak_running": bool(speak_up.get("ok")),
        "ears_running": bool(ears_up.get("ok")),
        "sudo": {k: r.get(k) for k in ("code", "stderr") if k in r},
        "user": {k: r2.get(k) for k in ("code", "stderr") if k in r2},
        "hint": None if ok else "pkill ran but speak_server did not return; check systemd units",
    }


def schedule_restart(delay_sec: float = 1.25) -> dict[str, Any]:
    """Restart after HTTP response can flush. Writes result to last-restart.json."""
    import json
    import threading
    import time

    status_path = LIVE / "last-restart.json"
    holder: dict[str, Any] = {"ok": None, "method": "scheduled", "pending": True}

    def _later() -> None:
        time.sleep(delay_sec)
        r = restart_services()
        holder.clear()
        holder.update(r)
        try:
            status_path.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass

    threading.Thread(target=_later, name="desk-atlas-restart", daemon=True).start()
    return holder


def run_update() -> dict[str, Any]:
    pulled = pull_upstream()
    if not pulled.get("ok"):
        return {
            "ok": False,
            "error": "pull failed",
            "pulled": {
                k: pulled.get(k)
                for k in ("via", "code", "stderr", "error")
                if pulled.get(k) is not None
            },
            "restarted": False,
            "spoke": False,
        }
    # Land newest desk_update.py before sync so SYNC_MAP/face rules apply even if
    # this process still has a stale import — also always-copy face inside sync_mapped.
    du_src = UPSTREAM / "software" / "speak" / "desk_update.py"
    if du_src.is_file():
        try:
            _copy_file(du_src, LIVE / "desk_update.py")
        except OSError:
            pass
    try:
        import importlib
        import desk_update as _du

        importlib.reload(_du)
        synced = _du.sync_mapped()
    except Exception:
        synced = sync_mapped()
    if not synced.get("ok"):
        return {
            "ok": False,
            "error": "sync failed",
            "pulled": True,
            "sync": synced,
            "restarted": False,
            "spoke": False,
        }
    # Speak before restart: restart kills this speak_server process.
    # Whisplay still hears TTS; services bounce ~1s after the HTTP response.
    spoke = speak_updated()
    schedule_restart(1.25)
    tip = pulled.get("tip")
    if not tip:
        lines = (pulled.get("stdout") or "").splitlines()
        tip = lines[-1] if lines else None
    return {
        "ok": True,
        "pulled": {"ok": True, "via": pulled.get("via"), "tip": tip},
        "sync": {
            "copied": synced.get("copied"),
            "skipped": synced.get("skipped"),
            "env_present": synced.get("env_present"),
        },
        "restarted": "scheduled",
        "spoke": spoke,
        "restart": {
            "method": "scheduled-after-response",
            "note": "units bounce ~1.25s after response; see LIVE/last-restart.json",
        },
        "error": None if spoke else "spoke failed (restart still scheduled)",
    }


def check_sender_auth(headers) -> bool:
    """Validate inbound update auth. Never log the key."""
    expected = (os.environ.get("ATLAS_SENDER_KEY") or "").strip()
    if not expected:
        return False
    header_name = (
        os.environ.get("ATLAS_SENDER_HEADER") or "Authorization"
    ).strip() or "Authorization"
    got = (headers.get(header_name) or "").strip()
    if not got:
        return False
    if header_name.lower() == "authorization":
        if expected.lower().startswith("bearer "):
            key_only = expected.split(None, 1)[1].strip()
            return got == expected or got == key_only or got == f"Bearer {key_only}"
        return got == expected or got == f"Bearer {expected}"
    return got == expected


def speak_updated() -> bool:
    """TTS + play "updated" after restart (same path as /speak). Never logs secrets."""
    try:
        from tts_xai import synthesize  # type: ignore
        from play_audio import play_bytes  # type: ignore
    except Exception:
        synthesize = None  # type: ignore
        play_bytes = None  # type: ignore
    if synthesize is not None and play_bytes is not None:
        try:
            audio = synthesize("updated")
            play_bytes(audio)
            return True
        except Exception:
            pass
    # Fallback: hit local /speak (no sender auth on mouth)
    try:
        import json
        import urllib.request

        port = int(os.environ.get("DESK_ATLAS_PORT", "8787"))
        host = os.environ.get("DESK_ATLAS_HOST", "127.0.0.1")
        req = urllib.request.Request(
            f"http://{host}:{port}/speak",
            data=json.dumps({"text": "updated"}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False
