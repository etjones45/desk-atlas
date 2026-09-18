"""Local ack line. No cloud LLM. Keyword + noun-echo fallback — never silent inventing."""

from __future__ import annotations

import re

_FALLBACK = "On it."

_FILLER = re.compile(
    r"\b(hey (?:atlas|grok|jarvis)|atlas|grok|jarvis|please|can you|could you|would you|"
    r"i want you to|i need you to|i need|i want|go ahead and|"
    r"real quick|quickly|just)\b",
    re.I,
)

# Obvious topic → natural ack (before generic noun echo).
_TOPIC_ACKS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\brecipe\b", re.I), "Let me find that recipe for you."),
    (re.compile(r"\b(movie|film)\b", re.I), "Looking into the movie details."),
    (re.compile(r"\b(concert|show|gig)\b", re.I), "Checking on that show."),
    (re.compile(r"\bflight\b", re.I), "Gathering flight information real quick."),
    (re.compile(r"\bbirthday\b", re.I), "Let me check on their birthday."),
    (re.compile(r"\b(doctor|dentist|appointment)\b", re.I), "Looking up that appointment."),
    (re.compile(r"\b(ticket|tickets|seats?)\b", re.I), "Looking for tickets now."),
    (re.compile(r"\bweather\b", re.I), "Checking the weather."),
    (re.compile(r"\b(email|inbox|gmail)\b", re.I), "Checking email."),
    (re.compile(r"\b(garage|myq)\b", re.I), "Checking the garage."),
    (re.compile(r"\b(temp(?:erature)?|thermostat|nest)\b", re.I), "Checking the thermostat."),
    (re.compile(r"\bcalendar\b.*\btomorrow\b|\btomorrow\b.*\bcalendar\b", re.I), "Checking tomorrow's calendar."),
    (re.compile(r"\bcalendar\b.*\btoday\b|\btoday\b.*\bcalendar\b", re.I), "Checking today's calendar."),
    (re.compile(r"\b(calendar|schedule|agenda)\b", re.I), "Checking the calendar."),
]

_STOP = {
    "a", "an", "the", "my", "our", "your", "their", "this", "that", "these", "those",
    "what", "when", "where", "who", "why", "how", "which", "is", "are", "was", "were",
    "do", "does", "did", "can", "could", "would", "should", "will", "to", "for", "of",
    "on", "in", "at", "with", "about", "me", "you", "it", "its", "be", "been", "being",
    "and", "or", "but", "if", "so", "just", "please", "hey", "grok", "atlas",
    "tell", "give", "show", "find", "get", "check", "look", "looking", "into", "up",
}


def _clean(text: str) -> str:
    t = (text or "").strip()
    t = _FILLER.sub(" ", t)
    t = re.sub(r"[?!.,]+$", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _noun_echo(low: str) -> str | None:
    """Pull a short noun phrase and echo it in a natural ack."""
    # "when is the/my X" / "when's X"
    m = re.search(
        r"\bwhen(?:'s| is| are| was| were)?\s+(?:the |my |our |their )?([a-z0-9][\w'-]*(?:\s+[a-z0-9][\w'-]*){0,3})",
        low,
    )
    if m:
        phrase = m.group(1).strip()
        words = [w for w in phrase.split() if w not in _STOP]
        if words:
            tip = " ".join(words[:4])
            if re.search(r"\b(birthday|anniversary)\b", tip):
                return f"Let me check on their {tip}."
            if re.search(r"\b(flight|movie|concert|show|appointment)\b", tip):
                return f"Looking into the {tip}."
            return f"Looking into the {tip}."

    # "find/get/check ... recipe|X"
    m = re.search(
        r"\b(find|get|check|look(?:ing)?(?:\s+for)?|search(?:ing)?(?:\s+for)?)\s+(?:me\s+)?(?:a |the |my |some )?(.{2,40})$",
        low,
    )
    if m:
        rest = re.sub(r"\b(for me|please)\b", "", m.group(2)).strip(" .")
        words = [w for w in rest.split() if w not in _STOP]
        if 0 < len(words) <= 5:
            tip = " ".join(words)
            if "recipe" in tip:
                return "Let me find that recipe for you."
            verb = m.group(1)
            if verb.startswith("check"):
                return f"Checking {tip}."
            return f"Looking for {tip} now."

    # Last resort: first content noun (3+ letters)
    tokens = re.findall(r"[a-z][a-z0-9'-]{2,}", low)
    content = [w for w in tokens if w not in _STOP]
    if content:
        tip = content[0]
        # Prefer a later more specific noun if first is bland
        for w in content:
            if w in {
                "recipe", "movie", "film", "concert", "show", "flight", "birthday",
                "appointment", "tickets", "ticket", "weather", "calendar", "email",
            }:
                tip = w
                break
        if tip == "recipe":
            return "Let me find that recipe for you."
        if tip in {"movie", "film"}:
            return "Looking into the movie details."
        if tip in {"concert", "show"}:
            return "Checking on that show."
        if tip == "flight":
            return "Gathering flight information real quick."
        if tip == "birthday":
            return "Let me check on their birthday."
        if tip == "appointment":
            return "Looking up that appointment."
        return f"On it — {tip}."

    return None


def ack_text(user_text: str) -> str:
    """Paraphrase a new request into a spoken ack. Never invent facts."""
    t = _clean(user_text)
    if not t:
        return _FALLBACK
    low = t.lower()

    for pat, line in _TOPIC_ACKS:
        if pat.search(low):
            return line

    echoed = _noun_echo(low)
    if echoed:
        return echoed

    return _FALLBACK
