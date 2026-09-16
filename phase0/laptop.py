#!/usr/bin/env python3
"""Desk Jarvis Phase-0 laptop script (Ethan).

Prove ears without hardware:
  - type text → webhook (or dropbox fallback)
  - optional: record mic WAV → xAI STT → webhook
  - optional: ping mouth /speak via tunnel URL

No wake word yet. No spend. Thread: desk-work.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DROPBOX = BASE / "dropbox"
CONFIG_PATH = BASE / "config.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def write_dropbox(text: str, note: str = "") -> Path:
    DROPBOX.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = DROPBOX / f"note-{ts}.json"
    payload = {
        "text": text,
        "thread": "desk-work",
        "source": "phase0-laptop",
        "note": note,
        "ts": ts,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def post_webhook(url: str, sender_key: str, text: str) -> tuple[int, str]:
    body = json.dumps(
        {
            "text": text,
            "thread": "desk-work",
            "source": "phase0-laptop",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Sender-Key": sender_key,
            "Authorization": f"Bearer {sender_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:500]
    except Exception as e:
        return 0, str(e)


def send_ears(text: str, webhook_url: str | None, sender_key: str | None) -> None:
    text = text.strip()
    if not text:
        print("empty text — nothing to send", file=sys.stderr)
        sys.exit(2)

    if webhook_url and sender_key and "PASTE_" not in webhook_url:
        code, body = post_webhook(webhook_url, sender_key, text)
        print(f"webhook HTTP {code}: {body}")
        if code and 200 <= code < 300:
            return
        path = write_dropbox(text, note=f"webhook failed HTTP {code}: {body}")
        print(f"dropbox fallback → {path}")
        return

    path = write_dropbox(text, note="webhook URL/key not set")
    print(f"no webhook configured — wrote dropbox {path}")
    print("For live ears: copy URL+key from Desk Jarvis voice-in panel and curl from your laptop (see curl-ears.example.sh). Do not paste keys into chat.")


def stt_file(wav_path: Path, api_key: str) -> str:
    # Prefer requests for multipart; fall back to curl.
    try:
        import requests

        with wav_path.open("rb") as f:
            r = requests.post(
                "https://api.x.ai/v1/stt",
                headers={"Authorization": f"Bearer {api_key}"},
                data=[("format", "true"), ("language", "en"), ("keyterm", "Jarvis")],
                files={"file": (wav_path.name, f, "audio/wav")},
                timeout=120,
            )
        r.raise_for_status()
        return (r.json().get("text") or "").strip()
    except ImportError:
        pass

    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        "https://api.x.ai/v1/stt",
        "-H",
        f"Authorization: Bearer {api_key}",
        "-F",
        "format=true",
        "-F",
        "language=en",
        "-F",
        "keyterm=Jarvis",
        "-F",
        f"file=@{wav_path}",
    ]
    out = subprocess.check_output(cmd, text=True)
    return (json.loads(out).get("text") or "").strip()


def record_wav(seconds: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # ffmpeg from default mic; Ethan can override with JARVIS_RECORD_DEVICE
    device = os.environ.get("JARVIS_RECORD_DEVICE", "default")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "alsa",
        "-i",
        device,
        "-t",
        str(seconds),
        "-ar",
        "16000",
        "-ac",
        "1",
        str(out),
    ]
    print(f"recording {seconds}s from {device}…")
    subprocess.run(cmd, check=True)


def ping_speak(speak_url: str, secret: str, text: str) -> None:
    url = speak_url.rstrip("/") + "/speak"
    body = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Jarvis-Speak-Secret": secret,
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        print(resp.read().decode("utf-8", errors="replace"))


def main() -> None:
    cfg = load_config()
    p = argparse.ArgumentParser(description="Desk Jarvis Phase-0 laptop bridge")
    p.add_argument("--text", help="Send this text as ears (skip mic)")
    p.add_argument("--record", type=float, metavar="SEC", help="Record N seconds then STT")
    p.add_argument("--wav", type=Path, help="Transcribe existing WAV/MP3 then send")
    p.add_argument("--speak-test", metavar="TEXT", help="POST text to mouth /speak")
    p.add_argument("--webhook-url", default=os.environ.get("JARVIS_WEBHOOK_URL") or cfg.get("webhook_url"))
    p.add_argument("--sender-key", default=os.environ.get("JARVIS_SENDER_KEY") or cfg.get("sender_key"))
    p.add_argument("--speak-url", default=os.environ.get("JARVIS_SPEAK_URL") or cfg.get("speak_url"))
    args = p.parse_args()

    if args.speak_test:
        secret = (BASE / "speak.secret").read_text(encoding="utf-8").strip()
        speak_url = args.speak_url
        if not speak_url:
            print("set speak_url in config.json or JARVIS_SPEAK_URL", file=sys.stderr)
            sys.exit(2)
        ping_speak(str(speak_url), secret, args.speak_test)
        return

    text = args.text
    if args.wav or args.record is not None:
        api_key = os.environ.get("XAI_API_KEY")
        if not api_key:
            print("XAI_API_KEY required for STT", file=sys.stderr)
            sys.exit(2)
        wav = args.wav
        if args.record is not None:
            wav = BASE / "phase0" / f"rec-{int(time.time())}.wav"
            record_wav(args.record, wav)
        assert wav is not None
        print(f"STT {wav}…")
        text = stt_file(wav, api_key)
        print(f"transcript: {text!r}")

    if not text:
        print("Provide --text, --record SEC, --wav FILE, or --speak-test TEXT", file=sys.stderr)
        sys.exit(2)

    send_ears(text, args.webhook_url, args.sender_key)


if __name__ == "__main__":
    main()
