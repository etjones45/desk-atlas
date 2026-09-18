#!/usr/bin/env python3
"""Grok-style matte sphere face for the Whisplay 240x280 panel.

The character is a single clay-blue ball that actually *rolls*: the eyes are
cut into the sphere in object space. Moods change color, lid shapes and motion.

Public API is unchanged, so speak_server keeps working:
    face.start(); face.set_state(\"talk\"); face.snapshot()

Laptop preview:
    DESK_ATLAS_FACE_PREVIEW=/tmp/desk-atlas-face.png python3 face.py
    python3 face.py --stills
    python3 face.py --clip idle 6
Pi: same file at ~/desk-atlas/face.py. Face failure never kills speech.
No API keys in this module.
"""
from __future__ import annotations
import math, os, random, sys, threading, time
try:
    import numpy as np
    _HAVE_NUMPY = True
except Exception:
    np = None
    _HAVE_NUMPY = False
WIDTH = int(os.environ.get("DESK_ATLAS_FACE_W", "240"))
HEIGHT = int(os.environ.get("DESK_ATLAS_FACE_H", "280"))
FPS = float(os.environ.get("DESK_ATLAS_FACE_FPS", "24"))
DONE_HOLD_SEC = float(os.environ.get("DESK_ATLAS_FACE_DONE_HOLD", "2.5"))
DITHER = os.environ.get("DESK_ATLAS_FACE_DITHER", "1").strip() not in ("0", "off", "no")
MOODS = {
    "idle":     dict(color=(57, 100, 208), led=(20, 70, 200)),
    "listen":   dict(color=(64, 122, 232), led=(40, 110, 255)),
    "think":    dict(color=(92, 104, 214), led=(120, 130, 235)),
    "talk":     dict(color=(58, 106, 220), led=(20, 80, 220)),
    "done":     dict(color=(44, 178, 112), led=(20, 180, 70)),
    "happy":    dict(color=(56, 164, 236), led=(40, 170, 255)),
    "error":    dict(color=(206, 62, 58),  led=(220, 20, 20)),
    "sad":      dict(color=(62, 96, 186),  led=(24, 46, 140)),
    "sleep":    dict(color=(48, 78, 168),  led=(10, 24, 80)),
    "surprise": dict(color=(74, 136, 244), led=(80, 150, 255)),
}
STATES = tuple(MOODS.keys())
_ALIAS = {"speak": "talk", "speaking": "talk", "ok": "done", "success": "done", "fail": "error", "thinking": "think", "listening": "listen", "sleepy": "sleep", "wake": "surprise", "smile": "happy"}
BG_TOP = (30, 30, 33)
BG_BOTTOM = (16, 16, 18)
