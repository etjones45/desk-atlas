# Desk Atlas ears (STT → voice-in webhook)

Record mic audio, transcribe with xAI STT, POST real `payload.text` to the Desk Atlas voice-in webhook. Replaces the old stub that posted a non-transcript placeholder.

## Files

| File | Role |
|------|------|
| `ears.py` | CLI: `--seconds 4` (default), `--wav PATH`, `--text` |
| `stt_xai.py` | xAI `POST /v1/stt` (requests or curl) |
| `webhook.py` | POST `{text, thread:"desk-work"}` with auth headers |
| `record.py` | `arecord` (Pi) or `ffmpeg` (Mac/Linux) → 16 kHz mono WAV |

## Deploy to Orange Pi

From Mac (after this package is in Documents):

```bash
scp -r ~/Documents/desk-atlas-laptop/ears orangepi@192.168.86.44:~/desk-atlas/
```

On the Pi, `.env` should already have `XAI_API_KEY`, `ATLAS_WEBHOOK_URL`, and `ATLAS_SENDER_KEY` from the earlier laptop package scp. Confirm keys are set (do not print values):

```bash
cd ~/desk-atlas
python3 -c "import os; from pathlib import Path
for line in Path('.env').read_text().splitlines():
  if '=' in line and not line.strip().startswith('#'):
    k=line.split('=',1)[0].strip(); v=line.split('=',1)[1].strip()
    if k in ('XAI_API_KEY','ATLAS_WEBHOOK_URL','ATLAS_SENDER_KEY'):
      print(k, 'SET' if v else 'MISSING')"
```

Run a 4-second listen:

```bash
cd ~/desk-atlas/ears
python3 ears.py --seconds 4
```

Typed webhook test (no mic):

```bash
python3 ears.py --text "Hey Atlas, ears wired"
```

## Env vars

- `XAI_API_KEY` — required for STT
- `ATLAS_WEBHOOK_URL` — Desk Atlas voice-in webhook URL
- `ATLAS_SENDER_KEY` — sender key from the voice-in panel
- `ATLAS_SENDER_HEADER` — optional; default Authorization (Bearer prefixed)
- `ATLAS_RECORD_DEVICE` — optional arecord/ffmpeg device override
- `ATLAS_DROPBOX` — optional override for failure notes dir (default `../dropbox`)

## Failure behavior

If STT fails, ears exits nonzero and writes a JSON note under `~/desk-atlas/dropbox` (or `/workspace/desk-atlas/dropbox`). It never posts a stub transcript to the webhook.

## Mac speak_server `/ears`

The laptop `speak_server.py` also exposes `POST /ears` for raw WAV or multipart `file=` audio: STT then the same voice-in path as `POST /voice-in`. Text `POST /voice-in` is unchanged.
