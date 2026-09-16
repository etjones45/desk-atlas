#!/usr/bin/env python3
"""Desk Jarvis ears CLI — record → xAI STT → voice-in webhook.

Never posts a stub/placeholder transcript. On STT failure: write a dropbox
note and exit nonzero.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow `python3 ears.py` from inside ears/ without installing a package.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from record import RecordError, record_wav  # noqa: E402
from stt_xai import SttError, stt_file  # noqa: E402
from webhook import WebhookError, post_voice_in  # noqa: E402

# Resolve desk-jarvis root: .../desk-jarvis/ears/ears.py → parents[1]
_EARS_DIR = _HERE
_BASE = _EARS_DIR.parent
# On Pi layout ~/desk-jarvis/ears → dropbox at ~/desk-jarvis/dropbox
# Also accept env override.
DROPBOX = Path(
    os.environ.get("JARVIS_DROPBOX")
    or (_BASE / "dropbox")
)


def write_dropbox(text: str, note: str = "", *, source: str = "ears") -> Path:
    DROPBOX.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = DROPBOX / f"note-{ts}.json"
    payload = {
        "text": text,
        "thread": "desk-work",
        "source": source,
        "note": note,
        "ts": ts,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def load_dotenv_quiet(path: Path) -> None:
    """Load KEY=VAL from .env into os.environ if not already set. Never print values."""
    if not path.is_file():
        return
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except OSError:
        pass


def env_flags() -> dict:
    """Safe diagnostics — names only, no values."""
    return {
        "XAI_API_KEY": bool(os.environ.get("XAI_API_KEY", "").strip()),
        "JARVIS_WEBHOOK_URL": bool(os.environ.get("JARVIS_WEBHOOK_URL", "").strip()),
        "JARVIS_SENDER_KEY": bool(os.environ.get("JARVIS_SENDER_KEY", "").strip()),
    }


def main() -> None:
    # Load .env from desk-jarvis root or ears/ parent (Pi: ~/desk-jarvis/.env)
    load_dotenv_quiet(_BASE / ".env")
    load_dotenv_quiet(_EARS_DIR / ".env")
    load_dotenv_quiet(Path.cwd() / ".env")

    p = argparse.ArgumentParser(
        description="Desk Jarvis ears: record → xAI STT → voice-in webhook"
    )
    p.add_argument(
        "--seconds",
        type=float,
        default=4.0,
        metavar="N",
        help="record N seconds then STT+webhook (default: 4)",
    )
    p.add_argument("--wav", type=Path, help="transcribe existing WAV/MP3 then webhook")
    p.add_argument("--text", help="send typed text (skip mic/STT) for webhook test")
    p.add_argument(
        "--no-webhook",
        action="store_true",
        help="print transcript only; do not POST webhook",
    )
    p.add_argument(
        "--keep-wav",
        action="store_true",
        help="keep temp recording under ears/tmp/",
    )
    args = p.parse_args()

    text: str | None = None
    wav_path: Path | None = None
    temp_wav = False

    try:
        if args.text is not None:
            text = args.text.strip()
            if not text:
                print("empty --text", file=sys.stderr)
                sys.exit(2)
        elif args.wav is not None:
            wav_path = args.wav
            print(f"STT {wav_path}…", file=sys.stderr)
            text = stt_file(wav_path)
        else:
            # Default path: record --seconds then STT
            tmp_dir = _EARS_DIR / "tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            wav_path = tmp_dir / f"rec-{int(time.time())}.wav"
            temp_wav = not args.keep_wav
            record_wav(args.seconds, wav_path)
            print(f"STT {wav_path}…", file=sys.stderr)
            text = stt_file(wav_path)
    except (RecordError, SttError) as e:
        note = f"ears failed: {e}"
        path = write_dropbox("", note=note, source="ears-error")
        print(f"ERROR: {e}", file=sys.stderr)
        print(f"dropbox note → {path}", file=sys.stderr)
        if temp_wav and wav_path and wav_path.is_file():
            try:
                wav_path.unlink()
            except OSError:
                pass
        sys.exit(1)

    assert text is not None
    print(f"transcript: {text!r}", file=sys.stderr)

    if args.no_webhook:
        print(text)
        if temp_wav and wav_path and wav_path.is_file():
            try:
                wav_path.unlink()
            except OSError:
                pass
        return

    try:
        code, body = post_voice_in(text, thread="desk-work", source="ears")
        print(f"webhook HTTP {code}: {body}", file=sys.stderr)
        if not (200 <= code < 300):
            path = write_dropbox(text, note=f"webhook HTTP {code}: {body}")
            print(f"dropbox fallback → {path}", file=sys.stderr)
            sys.exit(1)
    except WebhookError as e:
        path = write_dropbox(text, note=str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        print(f"dropbox fallback → {path}", file=sys.stderr)
        sys.exit(1)
    finally:
        if temp_wav and wav_path and wav_path.is_file():
            try:
                wav_path.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    main()
