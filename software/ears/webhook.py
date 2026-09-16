#!/usr/bin/env python3
"""POST Desk Jarvis voice-in webhook: {text, thread}.

Headers match phase0/laptop.py (Authorization Bearer + X-Sender-Key) and
Mac jarvis_webhook.py (JARVIS_SENDER_HEADER override). Never log sender keys.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULT_THREAD = "desk-work"
DEFAULT_SOURCE = "ears"


class WebhookError(RuntimeError):
    pass


def webhook_url() -> str:
    return (os.environ.get("JARVIS_WEBHOOK_URL") or "").strip()


def sender_key() -> str:
    return (os.environ.get("JARVIS_SENDER_KEY") or "").strip()


def sender_header_name() -> str:
    return (
        os.environ.get("JARVIS_SENDER_HEADER") or "Authorization"
    ).strip() or "Authorization"


def post_voice_in(
    text: str,
    *,
    thread: str = DEFAULT_THREAD,
    source: str = DEFAULT_SOURCE,
    url: str | None = None,
    sender_key_override: str | None = None,
) -> tuple[int, str]:
    """POST {text, thread, source}. Returns (http_status, body_snippet).

    Sends Authorization: Bearer <key> and X-Sender-Key: <key> by default
    (laptop.py style). If JARVIS_SENDER_HEADER is set to something other than
    Authorization, that header is used instead of Bearer.
    """
    text = (text or "").strip()
    if not text:
        raise WebhookError("empty text")

    target = (url if url is not None else webhook_url()).strip()
    key = (
        sender_key_override
        if sender_key_override is not None
        else sender_key()
    ).strip()
    if not target or "PASTE_" in target:
        raise WebhookError("JARVIS_WEBHOOK_URL is not set")
    if not key:
        raise WebhookError("JARVIS_SENDER_KEY is not set")

    body = json.dumps(
        {
            "text": text,
            "thread": thread or DEFAULT_THREAD,
            "source": source,
        }
    ).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "X-Sender-Key": key,
        "X-Automation-Key": key,
        "Authorization": f"Bearer {key}",
    }
    # Honoring JARVIS_SENDER_HEADER: if not Authorization, still keep Bearer +
    # X-Sender-Key, and add the custom header with the raw key.
    custom = sender_header_name()
    if custom.lower() not in ("authorization", "x-sender-key", "x-automation-key"):
        headers[custom] = key

    req = urllib.request.Request(target, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")[:500]
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise WebhookError(f"webhook HTTP {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise WebhookError(f"webhook network error: {e.reason}") from e
