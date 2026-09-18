# Desk Jarvis

Physical **Grok Bot** screen buddy for a desk: Orange Pi Zero 2W + PiSugar Whisplay HAT.

You talk → mic → STT → webhook into Jarvis → Jarvis replies out loud through TTS on the device. The 240×280 glass runs `software/speak/face.py` (live path `~/desk-atlas/face.py`).

## Hardware

| Piece | Notes |
|-------|--------|
| Orange Pi Zero 2W (2GB) | Board |
| PiSugar Whisplay HAT | 1.69″ LCD, dual mics, speaker, RGB, button |
| 40-pin hammer-in header | Stack interconnect |
| microSD + 5V USB-C PSU | Bookworm server image |
| M2.5×8 mm screws | Case (clamshell, not snap) |

Custom case STL/OpenSCAD: [`hardware/case/`](hardware/case/) (also mirrored in Google Drive).

## Architecture

```mermaid
flowchart LR
  Mic[Whisplay mics] --> Ears[software/ears STT]
  Ears -->|webhook text| Jarvis[Grok Bot Jarvis]
  Jarvis -->|POST /speak| Mouth[speak server + TTS]
  Mouth --> Spk[Whisplay speaker]
  Mouth --> Face[face.py on Whisplay LCD]
```

## Quick start

1. Flash Bookworm server on the Zero 2W (see [`docs/FLASH-WHEN-BOARD-ARRIVES.md`](docs/FLASH-WHEN-BOARD-ARRIVES.md) and [`phase2/`](phase2/)).
2. Copy `config/config.example.json` → local `config.json` (never commit secrets).
3. Put `XAI_API_KEY`, `ATLAS_WEBHOOK_URL` / `JARVIS_WEBHOOK_URL`, and `ATLAS_SENDER_KEY` / `JARVIS_SENDER_KEY` in a local `.env` on the Pi. Never commit that file.
4. Run ears: `python3 software/ears/ears.py --seconds 4`
5. Expose speak via named Cloudflare tunnel (example: `https://desk.etjarvis.com/speak`). Jarvis POSTs `{"text":"…","closer":true}`.
6. Face: `python3 software/speak/face.py --stills` on a laptop, or pull on the Pi so `desk_update` lands `face.py` next to `speak_server.py`.

## Repo layout

| Path | What |
|------|------|
| `software/ears/` | Record → xAI STT → voice-in webhook |
| `software/speak/` | TTS speak HTTP server + **face.py** (Pi name) |
| `software/speak/face.py` | Grok clay-sphere face. Syncs to `~/desk-atlas/face.py` |
| `docs/FACE.md` | Face moods, preview, OTA |
| `hardware/case/` | OpenSCAD + dims (+ STLs when present) |
| `deploy/` | systemd units + cloudflared examples |
| `docs/` | Flash, tunnel, blockers, phase 0 |
| `phase2/` | Pi install package + checklists |
| `config/` | `*.example` only |

## Security

**Do not commit:** `.env`, `speak.secret`, webhook sender keys, API keys, live tunnel credential JSON.

Face does not need its own key. Mouth/ears read `XAI_API_KEY` and sender keys from the Pi `.env` only.

Examples and docs stay key-free. Production speak URL for Ethan’s desk is a named tunnel; treat the **secret header / API keys** as private even when the hostname is public.

## Status

Phase 0 ears/mouth proven. Face standard is the object-space clay sphere in `software/speak/face.py` (OTA name `~/desk-atlas/face.py`). Keep secrets local.

Owners (personal ops): Hermes (software), Daedalus (hardware), Jarvis (PM / webhook), Octavian (this GitHub repo).

## License

MIT — see [`LICENSE`](LICENSE).
