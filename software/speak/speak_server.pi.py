#!/usr/bin/env python3
"""Desk Atlas laptop server (this process, not the old Phase 0 speak_server).

  POST /voice-in   desk inbox (JSON text). Unchanged.
                   idle + no recap → TTS ack + webhook in parallel
                   recap or already busy → webhook only
  POST /ears       raw WAV / multipart file / JSON base64 → xAI STT → same as /voice-in
  POST /speak      Atlas mouth. Point the tunnel here. Closer → idle.
  GET  /state      idle | busy + auth diagnostics (no secrets)
  POST /idle       force idle (test / recovery)
  POST /update     phone pull+sync+restart+speak "updated" (ATLAS_SENDER_*)
  POST /face       {"state": idle|talk|listen|think|done} — WhisPlay face

One server. Two processes = two mouths or a dead tunnel.
Ack and webhook start in the same instant. Neither waits on the other.
Secrets stay in the environment. Never print keys.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ack_text import ack_text
from atlas_webhook import auth_snapshot, post_voice_in
from local_intents import try_local
from desk_state import DeskState
from play_audio import play_bytes
from tts_xai import TtsError, synthesize

try:
    from desk_update import check_sender_auth, run_update
except ImportError:  # pragma: no cover
    try:
        from desk_update import check_sender_auth, run_update  # type: ignore
    except ImportError:
        check_sender_auth = None  # type: ignore
        run_update = None  # type: ignore


# ears STT (sibling package desk-atlas-laptop/ears/)
_EARS_DIR = Path(__file__).resolve().parent / "ears"
if _EARS_DIR.is_dir() and str(_EARS_DIR) not in sys.path:
    sys.path.insert(0, str(_EARS_DIR))
try:
    from stt_xai import SttError, stt_file  # type: ignore
except ImportError:  # pragma: no cover
    SttError = RuntimeError  # type: ignore
    stt_file = None  # type: ignore

try:
    import face as desk_face
except ImportError:  # pragma: no cover
    desk_face = None  # type: ignore

FACE_STATES = ("idle", "talk", "listen", "think", "done")

HOST = os.environ.get("DESK_ATLAS_HOST", "127.0.0.1")
PORT = int(os.environ.get("DESK_ATLAS_PORT", "8787"))
DRY_RUN = os.environ.get("DESK_ATLAS_DRY_RUN", "").strip() in ("1", "true", "yes")
IDLE_TIMEOUT = float(os.environ.get("DESK_ATLAS_IDLE_TIMEOUT", "180"))

STATE = DeskState(idle_timeout_sec=IDLE_TIMEOUT)
LAST_EVENTS: list[dict] = []
_EVENTS_LOCK = threading.Lock()


def _log_event(event: dict) -> None:
    with _EVENTS_LOCK:
        LAST_EVENTS.append(event)
        if len(LAST_EVENTS) > 40:
            del LAST_EVENTS[: len(LAST_EVENTS) - 40]
    line = {k: v for k, v in event.items() if k != "audio_bytes"}
    print(json.dumps(line, ensure_ascii=False), flush=True)


def _face(state: str) -> None:
    """Drive WhisPlay face. Best-effort; never raises into handlers."""
    state = (state or "").strip().lower()
    if state not in FACE_STATES:
        _log_event({"kind": "face", "error": "bad_state", "state": state})
        return
    if desk_face is None:
        return
    try:
        fn = getattr(desk_face, "set_state", None) or getattr(desk_face, "show", None)
        if callable(fn):
            fn(state)
        _log_event({"kind": "face", "state": state})
    except Exception as e:
        _log_event({"kind": "face", "error": str(e), "state": state})


def _start_face() -> None:
    if desk_face is None:
        _log_event({"kind": "face", "warn": "face_module_missing"})
        return
    try:
        start = getattr(desk_face, "start", None)
        if callable(start):
            start()
        _face("idle")
    except Exception as e:
        _log_event({"kind": "face", "error": f"start:{e}"})



def _speak_async(text: str, kind: str) -> None:
    def run() -> None:
        try:
            _face("talk")
            if DRY_RUN:
                _log_event({"kind": kind, "dry_run": True, "say": text})
                _face("idle")
                return
            audio = synthesize(text)
            _log_event({"kind": kind, "say": text, "bytes": len(audio)})
            play_bytes(audio)
            _face("done")
            _face("idle")
        except TtsError as e:
            _log_event({"kind": kind, "error": "tts", "detail": str(e)})
            _face("idle")
        except Exception as e:
            _log_event({"kind": kind, "error": "speak", "detail": str(e)})
            _face("idle")

    threading.Thread(target=run, name=f"tts-{kind}", daemon=True).start()


def _webhook_async(text: str, thread: str, recap: str | None) -> None:
    def run() -> None:
        try:
            if DRY_RUN:
                _log_event(
                    {
                        "kind": "webhook",
                        "dry_run": True,
                        "payload": {"text": text, "thread": thread, **({"recap": recap} if recap else {})},
                    }
                )
                return
            result = post_voice_in(text, thread=thread, recap=recap)
            _log_event({"kind": "webhook", "status": result.get("status")})
        except Exception as e:
            _log_event({"kind": "webhook", "error": str(e)})

    threading.Thread(target=run, name="atlas-webhook", daemon=True).start()


def handle_voice_in(body: dict) -> dict:
    text = str(body.get("text") or "").strip()
    thread = str(body.get("thread") or "desk-work").strip() or "desk-work"
    recap = body.get("recap")
    recap = str(recap).strip() if recap else ""

    if not text:
        return {"ok": False, "error": "text required"}

    _face("listen")

    # On-device: time/date etc. — answer + idle, no webhook round-trip.
    local = try_local(text)
    if local:
        _speak_async(local, kind="local")
        snap = STATE.snapshot()
        return {
            "ok": True,
            "local": True,
            "acked": False,
            "ack": None,
            "answer": local,
            "mode": snap["mode"],
            "thread": thread,
        }

    ack = None
    if STATE.should_ack(recap):
        ack = ack_text(text)
        # Busy is marked before either network call so a second curl cannot double-ack.
        STATE.mark_busy(thread)
        _speak_async(ack, kind="ack")
    else:
        STATE.mark_busy(thread)
        _face("think")

    _webhook_async(text, thread, recap or None)
    snap = STATE.snapshot()
    return {
        "ok": True,
        "local": False,
        "acked": bool(ack),
        "ack": ack,
        "mode": snap["mode"],
        "thread": thread,
    }


def handle_speak(body: dict) -> dict:
    text = str(body.get("text") or "").strip()
    closer = bool(body.get("closer"))
    if not text:
        return {"ok": False, "error": "text required"}
    closed = STATE.on_atlas_spoken(text, closer=closer)
    _speak_async(text, kind="mouth")
    return {"ok": True, "closer": closed, "mode": STATE.snapshot()["mode"]}



def _parse_multipart_file(content_type: str, raw: bytes) -> bytes | None:
    """Extract first file part body from multipart/form-data. Stdlib only."""
    if "multipart/form-data" not in content_type:
        return None
    boundary = None
    for part in content_type.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part.split("=", 1)[1].strip().strip('"')
            break
    if not boundary:
        return None
    sep = ("--" + boundary).encode("utf-8")
    for chunk in raw.split(sep):
        if b"Content-Disposition:" not in chunk:
            continue
        if b"filename=" not in chunk and b'name="file"' not in chunk and b"name=\"file\"" not in chunk:
            # still accept any part with a filename
            if b"filename=" not in chunk:
                continue
        head, _, body = chunk.partition(b"\r\n\r\n")
        if not body:
            head, _, body = chunk.partition(b"\n\n")
        if not body:
            continue
        if body.endswith(b"\r\n"):
            body = body[:-2]
        elif body.endswith(b"\n"):
            body = body[:-1]
        if body.endswith(b"--"):
            body = body[:-2]
        if body.endswith(b"\r\n"):
            body = body[:-2]
        return body
    return None


def handle_ears(raw: bytes, content_type: str, query_thread: str | None = None) -> dict:
    """STT audio then reuse voice-in path. Never invents a stub transcript."""
    if stt_file is None:
        return {"ok": False, "error": "ears/stt_xai not available"}

    ct = (content_type or "").split(";")[0].strip().lower()
    audio: bytes | None = None
    thread = (query_thread or "desk-work").strip() or "desk-work"

    if ct == "application/json":
        try:
            body = json.loads(raw.decode("utf-8") if raw else "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"ok": False, "error": "invalid json"}
        if isinstance(body, dict) and body.get("text"):
            # allow text passthrough on /ears too
            return handle_voice_in(body)
        b64 = ""
        if isinstance(body, dict):
            b64 = str(body.get("audio_base64") or body.get("wav_base64") or "")
            thread = str(body.get("thread") or thread).strip() or "desk-work"
        if not b64:
            return {"ok": False, "error": "audio_base64 or multipart/raw wav required"}
        import base64

        try:
            audio = base64.b64decode(b64)
        except Exception:
            return {"ok": False, "error": "invalid base64"}
    elif "multipart/form-data" in (content_type or ""):
        audio = _parse_multipart_file(content_type or "", raw)
        if audio is None:
            return {"ok": False, "error": "multipart file part not found"}
    elif ct in ("audio/wav", "audio/x-wav", "audio/wave", "application/octet-stream", "audio/mpeg", ""):
        audio = raw
    else:
        # try raw anyway
        audio = raw

    if not audio:
        return {"ok": False, "error": "empty audio body"}

    tmp = Path(__file__).resolve().parent / "ears" / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    wav_path = tmp / f"upload-{os.getpid()}.wav"
    try:
        wav_path.write_bytes(audio)
        try:
            _face("listen")
            _face("think")
            text = stt_file(wav_path)
        except Exception as e:
            _log_event({"kind": "ears", "error": "stt", "detail": str(e)})
            _face("idle")
            return {"ok": False, "error": f"stt failed: {e}"}
    finally:
        try:
            wav_path.unlink(missing_ok=True)
        except OSError:
            pass

    return handle_voice_in({"text": text, "thread": thread})


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("http " + (fmt % args) + "\n")

    def _json(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?")[0] == "/state":
            snap = STATE.snapshot()
            snap.update(auth_snapshot())
            snap["listen"] = f"http://{HOST}:{PORT}"
            snap["this_is"] = "desk-atlas speak_server"
            snap["face"] = desk_face is not None
            with _EVENTS_LOCK:
                snap["recent"] = list(LAST_EVENTS[-8:])
            self._json(200, snap)
            return
        if self.path.split("?")[0] == "/health":
            self._json(
                200,
                {"ok": True, "dry_run": DRY_RUN, "listen": f"http://{HOST}:{PORT}"},
            )
            return
        self._json(404, {"ok": False, "error": "not found"})

    def _read_raw(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return b""
        return self.rfile.read(length)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]
        try:
            if path == "/ears":
                raw = self._read_raw()
                ct = self.headers.get("Content-Type", "")
                result = handle_ears(raw, ct)
                code = 200 if result.get("ok") else 400
                if result.get("error", "").startswith("stt failed"):
                    code = 502
                self._json(code, result)
                return
            try:
                body = self._read_json()
            except json.JSONDecodeError:
                self._json(400, {"ok": False, "error": "invalid json"})
                return
            if path in ("/voice-in", "/voice_in", "/in"):
                self._json(200, handle_voice_in(body))
                return
            if path == "/speak":
                self._json(200, handle_speak(body))
                return
            if path in ("/idle", "/state/idle"):
                reason = STATE.mark_idle("manual")
                _face("idle")
                self._json(200, {"ok": True, "mode": "idle", "reason": reason})
                return
            if path == "/face":
                state = str((body or {}).get("state") or "").strip().lower()
                if state not in FACE_STATES:
                    self._json(
                        400,
                        {"ok": False, "error": "state required", "allowed": list(FACE_STATES)},
                    )
                    return
                _face(state)
                snap = desk_face.FACE.snapshot() if desk_face is not None else {"board": False}
                self._json(200, {"ok": True, "state": state, "face": desk_face is not None, **snap})
                return
            if path == "/update":
                if check_sender_auth is None or run_update is None:
                    self._json(500, {"ok": False, "error": "desk_update missing"})
                    return
                if not check_sender_auth(self.headers):
                    self._json(401, {"ok": False, "error": "unauthorized"})
                    return
                # Body optional; ignore unknown fields
                _ = body if isinstance(body, dict) else {}
                result = run_update()
                payload = {
                    "ok": bool(result.get("ok")),
                    "pulled": result.get("pulled"),
                    "restarted": bool(result.get("restarted")),
                    "spoke": bool(result.get("spoke")),
                }
                if result.get("sync"):
                    payload["sync"] = result.get("sync")
                if result.get("restart"):
                    payload["restart"] = result.get("restart")
                if result.get("error"):
                    payload["error"] = result.get("error")
                code = 200 if payload["ok"] else 500
                if result.get("error") == "pull failed":
                    code = 502
                self._json(code, payload)
                return
            self._json(404, {"ok": False, "error": "not found"})
        except Exception:
            traceback.print_exc()
            self._json(500, {"ok": False, "error": "server"})


def main() -> None:
    _start_face()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(
        json.dumps(
            {
                "listening": f"http://{HOST}:{PORT}",
                "dry_run": DRY_RUN,
                "idle_timeout_sec": IDLE_TIMEOUT,
                "face": desk_face is not None,
            }
        ),
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
