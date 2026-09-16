#!/usr/bin/env python3
"""Desk Atlas speak server — Phase 0 mouth endpoint (stdlib only)."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
SECRET_PATH = BASE / "speak.secret"
LOG_PATH = BASE / "speak.log"
MP3_PATH = BASE / "last_speak.mp3"
MAX_TEXT = 800
TTS_URL = "https://api.x.ai/v1/tts"
PORT = int(os.environ.get("ATLAS_SPEAK_PORT", "8080"))
VOICE = os.environ.get("ATLAS_VOICE", "eve")
PLAY = os.environ.get("ATLAS_PLAY", "1") != "0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("atlas-speak")


def load_secret() -> str | None:
    try:
        return SECRET_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        log.info("%s - %s", self.address_string(), fmt % args)

    def _send_json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] != "/health":
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        secret = load_secret()
        self._send_json(200, {"ok": True, "has_key": bool(secret)})

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/speak":
            self._send_json(404, {"ok": False, "error": "not found"})
            return

        secret = load_secret()
        if not secret:
            self._send_json(500, {"ok": False, "error": "speak.secret missing"})
            return

        got = self.headers.get("X-Atlas-Speak-Secret", "")
        if got != secret:
            log.warning("speak auth failed from %s", self.address_string())
            self._send_json(401, {"ok": False, "error": "unauthorized"})
            return

        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"ok": False, "error": "invalid json"})
            return

        text = data.get("text") if isinstance(data, dict) else None
        if not isinstance(text, str) or not text.strip():
            self._send_json(400, {"ok": False, "error": "text required"})
            return

        text = text.strip()
        if len(text) > MAX_TEXT:
            text = text[:MAX_TEXT]
            log.info("text truncated to %d chars", MAX_TEXT)

        api_key = os.environ.get("XAI_API_KEY")
        if not api_key:
            log.error("XAI_API_KEY missing")
            self._send_json(500, {"ok": False, "error": "missing XAI_API_KEY"})
            return

        payload = json.dumps(
            {
                "text": text,
                "voice_id": VOICE,
                "language": "en",
                "text_normalization": True,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            TTS_URL,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
        )

        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                audio = resp.read()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
            log.error("TTS HTTP %s: %s", e.code, err_body)
            self._send_json(
                502,
                {"ok": False, "error": f"tts http {e.code}", "detail": err_body},
            )
            return
        except Exception as e:
            log.exception("TTS request failed")
            self._send_json(502, {"ok": False, "error": str(e)})
            return

        try:
            MP3_PATH.write_bytes(audio)
        except OSError as e:
            log.error("failed to write mp3: %s", e)
            self._send_json(500, {"ok": False, "error": "write mp3 failed"})
            return

        if PLAY:
            try:
                subprocess.run(
                    [
                        "ffplay",
                        "-nodisp",
                        "-autoexit",
                        "-loglevel",
                        "quiet",
                        str(MP3_PATH),
                    ],
                    check=False,
                    timeout=120,
                )
            except Exception as e:
                log.warning("ffplay failed: %s", e)

        ms = int((time.monotonic() - t0) * 1000)
        nbytes = len(audio)
        log.info("speak ok ms=%d bytes=%d voice=%s", ms, nbytes, VOICE)
        self._send_json(200, {"ok": True, "ms": ms, "bytes": nbytes})


def main() -> None:
    secret = load_secret()
    log.info(
        "starting speak server on 0.0.0.0:%d has_secret=%s play=%s voice=%s",
        PORT,
        bool(secret),
        PLAY,
        VOICE,
    )
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
