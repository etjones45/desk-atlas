#!/usr/bin/env bash
# Desk Jarvis ears — run on YOUR laptop. Copy URL + sender key from the
# Desk Jarvis voice-in routine panel. Do not paste keys into chat or into
# shared /workspace/desk-jarvis/config.json.
set -euo pipefail

WEBHOOK_URL="PASTE_WEBHOOK_URL"
SENDER_KEY="PASTE_SENDER_KEY"

curl -sS -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -H "X-Sender-Key: $SENDER_KEY" \
  -d '{"text":"Desk Jarvis ears test — phase 0","thread":"desk-work","source":"phase0-curl"}'

echo
