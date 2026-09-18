# Desk Atlas — Cloudflare tunnel

Mouth path: **Atlas → HTTPS tunnel → Pi `speak_server.py` → xAI TTS → WhisPlay speaker**.

## Phase 0 (this box / Ethan laptop)

Quick tunnel (no account config):

```bash
# terminal A
cd /workspace/desk-atlas
ATLAS_PLAY=0 python3 speak_server.py

# terminal B
cloudflared tunnel --url http://127.0.0.1:8080
```

Copy the `https://….trycloudflare.com` URL into `config.json` as `speak_url`, and tell Atlas that mouth URL for `/speak` POSTs.

Header: `X-Atlas-Speak-Secret: <contents of speak.secret>`  
Body: `{"text":"short spoken reply"}`

## When the board ships

1. Install `cloudflared` on the Orange Pi (same binary Atlas already has on the shared computer).
2. Prefer a **named** tunnel + hostname once ready (see `cloudflared/config.example.yml`).
3. Until named domain: keep quick tunnel; update Atlas `speak_url` whenever the trycloudflare URL rotates.
4. Enable `systemd/cloudflared-desk-atlas.service` after `desk-atlas-speak.service`.

## Security

- Never commit `speak.secret` or tunnel credentials.
- Speak server rejects bad `X-Atlas-Speak-Secret` with 401.
- Do not expose without the secret header.

## Away / Tesla Guest

LAN SSH often fails on Guest (client isolation). Use **Tailscale** for admin access — see `docs/TAILSCALE.md`. Day-to-day mouth still uses this tunnel.
