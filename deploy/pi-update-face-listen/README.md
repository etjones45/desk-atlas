# Desk Atlas Pi update — face + Hey Grok listen ears

## Package (Octavian / Hermes)

Canonical box paths (CopyFromBox):

| File | Role |
|------|------|
| `/workspace/desk-atlas/pi-update-deploy/speak_server.py` | Mouth with `/update` + restored face hooks |
| `/workspace/desk-atlas/pi-update-deploy/ears.py` | CLI + `--listen` (Hey Grok) |
| `/workspace/desk-atlas/pi-update-deploy/desk_update.py` | Sync map protects listen ears |
| `/workspace/desk-atlas/pi-update-deploy/deploy-via-mac.sh` | scp + restart + probe |

## Deploy (Mac Shell machineId `060a321a-71ef-4a39-8be6-0ef9647aba28`)

1. CopyFromBox the four files above → Mac `~/Documents/desk-atlas-pi-update/`
2. `SRC_DIR=~/Documents/desk-atlas-pi-update bash deploy-via-mac.sh`

## Hey Grok

- Prefer openwakeword if `models/hey_grok.onnx` (or `DESK_WAKE_MODEL`) exists
- Else STT keyphrase interim (`DESK_WAKE_PHRASE` default `hey grok`)
- Stock OWW `hey_jarvis` is **not** used

## Face

- Idle on speak_server start
- Listen on wake (`face.set_state("listen")` or `POST /face`)
- Talk/think/done on speak / voice-in paths

## Blocker

Sand worker Shell is box-only (no Mac machineId). Pi is LAN-only. Hermes must run Mac deploy.
