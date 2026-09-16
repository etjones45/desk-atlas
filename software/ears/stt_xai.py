#!/usr/bin/env python3
"""xAI speech-to-text helper for Desk Atlas ears.

POST https://api.x.ai/v1/stt — same contract as phase0/laptop.py stt_file.
Never log or print the API key.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


STT_URL = "https://api.x.ai/v1/stt"


class SttError(RuntimeError):
    pass


def api_key_from_env() -> str:
    key = (os.environ.get("XAI_API_KEY") or "").strip()
    if not key:
        raise SttError("XAI_API_KEY is not set")
    return key


def stt_file(wav_path: Path, api_key: str | None = None) -> str:
    """Transcribe a WAV/audio file via xAI STT. Returns stripped text.

    Prefers requests multipart; falls back to curl -F.
    Raises SttError on failure or empty transcript.
    """
    wav_path = Path(wav_path)
    if not wav_path.is_file():
        raise SttError(f"audio file not found: {wav_path}")

    key = api_key if api_key is not None else api_key_from_env()
    text = _stt_requests(wav_path, key)
    if text is None:
        text = _stt_curl(wav_path, key)
    text = (text or "").strip()
    if not text:
        raise SttError("STT returned empty transcript")
    return text


def _stt_requests(wav_path: Path, api_key: str) -> str | None:
    try:
        import requests
    except ImportError:
        return None

    try:
        with wav_path.open("rb") as f:
            r = requests.post(
                STT_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                data=[("format", "true"), ("language", "en"), ("keyterm", "Atlas")],
                files={"file": (wav_path.name, f, "audio/wav")},
                timeout=120,
            )
        if r.status_code >= 400:
            raise SttError(f"STT HTTP {r.status_code}")
        return (r.json().get("text") or "").strip()
    except SttError:
        raise
    except Exception as e:
        raise SttError(f"STT request failed: {e}") from e


def _stt_curl(wav_path: Path, api_key: str) -> str:
    cmd = [
        "curl",
        "-sS",
        "-X",
        "POST",
        STT_URL,
        "-H",
        f"Authorization: Bearer {api_key}",
        "-F",
        "format=true",
        "-F",
        "language=en",
        "-F",
        "keyterm=Atlas",
        "-F",
        f"file=@{wav_path}",
    ]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise SttError(f"STT curl failed (exit {e.returncode})") from e
    except FileNotFoundError as e:
        raise SttError("curl not found and requests not installed") from e
    try:
        return (json.loads(out).get("text") or "").strip()
    except json.JSONDecodeError as e:
        raise SttError("STT response was not JSON") from e
