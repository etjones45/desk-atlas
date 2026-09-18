# Desk Atlas face

Canonical file: `software/speak/face.py`

On the Pi, `desk_update.py` copies that file to `~/desk-atlas/face.py`.
`speak_server` imports `face` from the live folder. Do not rename it
(`GrokBot Face.py` is the source nickname only — the Pi name is `face.py`).

Public API (unchanged):

```
face.start()
face.set_state("listen")   # idle listen think talk done happy error sad sleep surprise
face.set_state("error", "NET")
face.snapshot()
```

No API keys live in this module. TTS / webhook / OTA keys stay in
`~/desk-atlas/.env` on the Pi (never git).

## Env (optional)

```
DESK_ATLAS_FACE=1
DESK_ATLAS_FACE_W=240
DESK_ATLAS_FACE_H=280
DESK_ATLAS_FACE_FPS=24
DESK_ATLAS_FACE_PREVIEW=/tmp/desk-atlas-face.png
```

Required for mouth / ears / OTA — already on the Pi `.env`, not in this file:

```
XAI_API_KEY
ATLAS_WEBHOOK_URL
ATLAS_SENDER_KEY
ATLAS_SENDER_HEADER=Authorization
```

House mouth URL (named tunnel, not a secret): `https://desk.etjarvis.com/speak`

## Laptop

```
cd software/speak
DESK_ATLAS_FACE_PREVIEW=/tmp/desk-atlas-face.png python3 face.py
python3 face.py --stills
python3 face.py --clip idle 6
```

## Pi after this commit

```
~/bin/desk-atlas-pull
# or POST /update with sender auth
sudo systemctl restart desk-atlas
```

Force a mood:

```
curl -s -X POST http://127.0.0.1:8787/face \
  -H 'Content-Type: application/json' \
  -d '{"state":"listen"}'
```

Do not put XAI_API_KEY, ATLAS_SENDER_KEY, or tunnel tokens in this repo.
