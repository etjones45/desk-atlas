# Desk Jarvis — Phase 0 (Ethan test)

Goal: prove **ears** (webhook in) and **mouth** (TTS out) before buying hardware.

Routine: **Desk Jarvis voice-in** (`desk-jarvis-voice-in`). Soft owners: Hermes software, Daedalus cart, Jarvis PM.

## Ears (webhook) — Ethan’s laptop

1. Open the **Desk Jarvis voice-in** routine panel in Grok Bot.
2. Copy the webhook **URL** and **sender key** yourself (never paste them into chat).
3. From your laptop, fill placeholders in `phase0/curl-ears.example.sh` **locally** (or inline curl) and run. Confirm Jarvis gets the text on the desk-work thread.

Do **not** write URL/key into committed config files.

Typed stand-in (no webhook key needed — dropbox only on the shared computer):

```bash
python3 phase0/laptop.py --text "Hey Jarvis, phase 0 ears check"
```

## Mouth (speak + tunnel)

1. Speak server:

   ```bash
   JARVIS_PLAY=0 python3 software/speak/speak_server.py   # needs XAI_API_KEY in env for real TTS
   curl -s http://127.0.0.1:8080/health
   ```

2. After `XAI_API_KEY` is set, start a Cloudflare tunnel and point Jarvis at the public `/speak` URL (not the speak secret).

3. Jarvis POSTs short spoken lines to `{speak_url}` with body `{"text":"…","closer":true}` (and any local auth your speak server expects).

## Laptop helpers

```bash
python3 phase0/laptop.py --text "…"          # dropbox if no local webhook env
python3 phase0/laptop.py --record 4          # needs XAI_API_KEY
python3 phase0/laptop.py --speak-test "…"    # needs speak_url + server key
```

Wake sketch (board later): `docs/wake_sketch.md`.  
Tunnel / flash / blockers: `docs/TUNNEL.md`, `docs/FLASH-WHEN-BOARD-ARRIVES.md`, `docs/BLOCKERS.md`.

## Go / no-go

**Go** if ears deliver text via Ethan’s panel curl and mouth returns TTS through the tunnel.

Then cart hardware (Orange Pi Zero 2W 2GB + hammer-in header + WhisPlay + 5V 2A+ USB-C + 32GB microSD).

**No-go** if webhook or TTS/tunnel fails — fix software first.
