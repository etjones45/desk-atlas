# Phone POST /update

Endpoint: `POST https://desk.etjarvis.com/update`

Auth: `ATLAS_SENDER_HEADER` (default `Authorization`) + `ATLAS_SENDER_KEY`.
If header is Authorization, both raw key and `Bearer <key>` are accepted.

Actions (in `desk_update.py`):
1. `~/bin/desk-atlas-pull` or `git fetch` + `git pull --ff-only` in `~/desk-atlas-upstream`
2. Sync mapped files into live `~/desk-atlas` (never deletes `.env`, `venv`, absent `face.py`, `*.bak`, `__pycache__`)
3. Schedule `systemctl restart desk-atlas.service desk-atlas-ears.service` (~1s after HTTP response — restart would kill the handler mid-request)
4. Speak “updated” via TTS/play (same stack as `/speak`) before the bounce

## Sync map
| Upstream | Live |
|----------|------|
| `software/speak/desk_update.py` | `desk_update.py` |
| `software/speak/speak_server*.py` (only if contains `/update`) | `speak_server.py` |
| `software/speak/tts_xai.py` (+ ack/webhook/state/play if present) | flat live names |
| `software/ears/ears.py` (+ stt/webhook/record helpers) | `ears.py` (+ helpers) |

Deploy helpers: `/workspace/desk-atlas/pi-update-deploy/`
