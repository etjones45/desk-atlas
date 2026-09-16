# Phase 2 — Secret / key handoff (never in chat)

## Rules

- **Never** paste `XAI_API_KEY`, `speak.secret`, Cloudflare tunnel tokens, or webhook sender keys into Grok Bot chat.
- Ethan places keys **on the Pi filesystem** himself (or Atlas uses secure card → Hermes loads only on shared computer Phase 0 style).

## On the Pi (`/opt/desk-atlas/`)

| File | Who creates | Notes |
| --- | --- | --- |
| `env` | Ethan (from `env.example`) | `chmod 600`; set `XAI_API_KEY=` locally |
| `speak.secret` | `install-desk-atlas.sh` generates **or** Hermes provides offline copy of Phase-0 secret | Must match what Atlas POSTs as `X-Atlas-Speak-Secret` |
| `config.json` | install script | `speak_url` filled after named tunnel exists |

## Shared-computer Phase 0 reference (already exists)

- Speak secret file: `/workspace/desk-atlas/speak.secret` (do not print)
- xAI connector store (Atlas): `/home/box/sand-data/connector-secrets/<atlas-id>/xai.json` — Hermes may load into speak process env; never echo value

## Webhook ears

Still Ethan-only: copy URL + sender key from **Desk Atlas voice-in** routine panel; curl from laptop. Keep off shared `config.json`.
