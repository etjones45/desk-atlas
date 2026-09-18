#!/usr/bin/env bash
# Optional Tailscale health for Desk Atlas Pi.
# Exit 0 if tailscaled is up and has an IPv4. Non-zero otherwise.
# Desk voice/tunnel must NOT depend on this — admin mesh only.
set -euo pipefail

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale: not installed (see docs/TAILSCALE.md)"
  exit 1
fi

if ! systemctl is-active --quiet tailscaled 2>/dev/null; then
  echo "tailscaled: inactive — try: sudo systemctl enable --now tailscaled"
  exit 2
fi

ip4="$(tailscale ip -4 2>/dev/null | head -n1 || true)"
if [[ -z "${ip4}" ]]; then
  echo "tailscale: no IPv4 — run: sudo tailscale up"
  exit 3
fi

echo "tailscale ok: ${ip4}"
tailscale status --self 2>/dev/null | head -n 3 || true
exit 0
