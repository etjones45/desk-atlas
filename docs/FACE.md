# Desk Atlas face

Canonical file: `software/speak/face.py`

On the Pi, `desk_update.py` copies that file to `~/desk-atlas/face.py`.
`speak_server` imports `face` from the live folder. Do not rename it.

## API

```
face.start()
face.set_state("listen")   # also talk, think, done, error, happy, sad, sleep, surprise
face.snapshot()
```

No API keys live in this module. TTS / webhook keys stay in `~/desk-atlas/.env` on the Pi (never git).

## Env (optional)

```
DESK_ATLAS_FACE=1
DESK_ATLAS_FACE_W=240
DESK_ATLAS_FACE_H=280
DESK_ATLAS_FACE_FPS=24
DESK_ATLAS_FACE_PREVIEW=/tmp/desk-atlas-face.png
```

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

Do not put XAI_API_KEY, ATLAS_SENDER_KEY, or tunnel tokens in this repo.
