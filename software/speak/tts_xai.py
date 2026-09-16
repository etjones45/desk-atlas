"""Same xAI TTS the mouth already uses. REST first (short acks). Key from env only."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

TTS_URL = os.environ.get("XAI_TTS_URL", "https://api.x.ai/v1/tts")
# Use whatever the existing speak script already has. Do not shop voices here.
TTS_VOICE = os.environ.get("XAI_TTS_VOICE", os.environ.get("TTS_VOICE", "eve"))
TTS_LANGUAGE = os.environ.get("XAI_TTS_LANGUAGE", "en")
TTS_CODEC = os.environ.get("XAI_TTS_CODEC", "mp3")


class TtsError(RuntimeError):
    pass


def _api_key() -> str:
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        raise TtsError("XAI_API_KEY is not set")
    return key


def synthesize(text: str) -> bytes:
    """Return audio bytes (mp3 by default). Never logs the key."""
    body = json.dumps(
        {
            "text": text,
            "voice_id": TTS_VOICE,
            "language": TTS_LANGUAGE,
            "output_format": {"codec": TTS_CODEC, "sample_rate": 24000},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        TTS_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
            "Accept": "application/octet-stream",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise TtsError(f"TTS HTTP {e.code}") from None
    except urllib.error.URLError as e:
        raise TtsError(f"TTS network error: {e.reason}") from None
