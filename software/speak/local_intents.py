"""On-device intents that answer instantly — no webhook round-trip."""

from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

# Ethan / desk default
_TZ = ZoneInfo("America/Denver")

_TIME = re.compile(
    r"^\s*(hey (?:grok|atlas|jarvis)[, ]*)?"
    r"(what(?:'s| is)?\s+the\s+time|what\s+time\s+is\s+it|tell\s+me\s+the\s+time|"
    r"current\s+time|time\s+now)\s*[?.!]?\s*$",
    re.I,
)
_DATE = re.compile(
    r"^\s*(hey (?:grok|atlas|jarvis)[, ]*)?"
    r"(what(?:'s| is)?\s+(?:the\s+)?(?:date|day)(?:\s+today)?|"
    r"what(?:'s| is)?\s+today(?:'s)?\s+date|what\s+day\s+is\s+it|"
    r"today(?:'s)?\s+date)\s*[?.!]?\s*$",
    re.I,
)


def _clock_phrase(now: datetime) -> str:
    h = now.hour % 12 or 12
    ampm = "AM" if now.hour < 12 else "PM"
    return f"It's {h}:{now.minute:02d} {ampm}."


def _date_phrase(now: datetime) -> str:
    return f"Today is {now.strftime('%A, %B')} {now.day}, {now.year}."


def try_local(text: str) -> str | None:
    """Return a spoken answer if handled on-device, else None."""
    t = (text or "").strip()
    if not t:
        return None
    if _TIME.match(t):
        return _clock_phrase(datetime.now(_TZ))
    if _DATE.match(t):
        return _date_phrase(datetime.now(_TZ))
    return None
