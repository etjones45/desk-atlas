# Desk Jarvis ears (STT → voice-in webhook)

Record mic audio, transcribe with xAI STT, POST real `payload.text` to the Desk Jarvis voice-in webhook. Replaces the old stub that posted a non-transcript placeholder.

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
scp -r ~/Documents/desk-jarvis-laptop/ears orangepi@192.168.86.44:~/desk-jarvis/
```

On the Pi, `.env` should already have `XAI_API_KEY`, `JARVIS_WEBHOOK_URL`, and `JARVIS_SENDER_KEY` from the earlier laptop package scp. Confirm keys are set (do not print values):

```bash
cd ~/desk-jarvis
python3 -c "import os; from pathlib import Path
for line in Path('.env').read_text().splitlines():
  if '=' in line and not line.strip().startswith('#'):
    k=line.split('=',1)[0].strip(); v=line.split('=',1)[1].strip()
    if k in ('XAI_API_KEY','JARVIS_WEBHOOK_URL','JARVIS_SENDER_KEY'):
      print(k, 'SET' if v else 'MISSING')"
```

Run a 4-second listen:

```bash
cd ~/desk-jarvis/ears
python3 ears.py --seconds 4
```

Typed webhook test (no mic):

```bash
python3 ears.py --text "Hey Jarvis, ears wired"
```

## Env vars

- `XAI_API_KEY` — required for STT
- `JARVIS_WEBHOOK_URL` — Desk Jarvis voice-in webhook URL
- `JARVIS_SENDER_KEY` — sender key from the voice-in panel
- `JARVIS_SENDER_HEADER` — optional; default Authorization (Bearer prefixed)
- `JARVIS_RECORD_DEVICE` — optional arecord/ffmpeg device override
- `JARVIS_DROPBOX` — optional override for failure notes dir (default `../dropbox`)

## Failure behavior

If STT fails, ears exits nonzero and writes a JSON note under `~/desk-jarvis/dropbox` (or `/workspace/desk-jarvis/dropbox`). It never posts a stub transcript to the webhook.

## Mac speak_server `/ears`

The laptop `speak_server.py` also exposes `POST /ears` for raw WAV or multipart `file=` audio: STT then the same voice-in path as `POST /voice-in`. Text `POST /voice-in` is unchanged.
