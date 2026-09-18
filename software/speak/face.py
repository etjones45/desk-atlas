#!/usr/bin/env python3
"""Grok-style matte sphere face for the Whisplay 240x280 panel.

Looks like the reference: full clay-blue ball, two recessed oval holes,
soft studio light, blink that squashes tall ovals into slits.

Animation moods (speak_server drives these):
  idle   — lively blinks + look-around roll + breathing bob (~50% more motion)
  listen — scales up / leans forward (depth) + cyan on Hey Grok
  think  — stronger color cycle + restless bounce while Atlas works
  talk   — conversational bob + warm engaging eyes
  done/error — readable, punchier cue

speak_server calls set_state(). Laptop preview:
  DESK_ATLAS_FACE_PREVIEW=/tmp/desk-atlas-face.png python3 face.py
Pi: same file at ~/desk-atlas/face.py. Face failure never kills speech.
"""

from __future__ import annotations

import math
import os
import random
import sys
import threading
import time

WIDTH = int(os.environ.get("DESK_ATLAS_FACE_W", "240"))
HEIGHT = int(os.environ.get("DESK_ATLAS_FACE_H", "280"))
FPS = float(os.environ.get("DESK_ATLAS_FACE_FPS", "15"))
DONE_HOLD_SEC = float(os.environ.get("DESK_ATLAS_FACE_DONE_HOLD", "2.5"))

STATES = ("idle", "listen", "think", "talk", "done", "error")

# Matte clay colors — idle matches the reference ball.
COLORS = {
    "idle": (28, 92, 228),
    "listen": (0, 220, 240),  # vivid cyan — unmistakable vs idle blue
    "think": (150, 95, 255),  # base; _render shifts while busy
    "talk": (36, 108, 235),  # slightly warmer/engaging blue
    "done": (24, 185, 82),
    "error": (210, 32, 32),
}
LED = {
    "idle": (20, 70, 200),
    "listen": (0, 240, 255),
    "think": (170, 90, 255),
    "talk": (28, 85, 220),
    "done": (18, 200, 75),
    "error": (235, 18, 18),
}
# Busy (think) color cycle — punchier blue → cyan → purple → magenta-blue
_THINK_PALETTE = (
    (55, 85, 255),
    (0, 230, 245),
    (210, 70, 255),
    (30, 160, 255),
    (160, 60, 255),
)
BG = (18, 18, 20)

# Studio key light, upper-left, matching the reference frames.
_LX, _LY, _LZ = -0.42, -0.52, 0.75
_LN = math.sqrt(_LX * _LX + _LY * _LY + _LZ * _LZ)
_LX, _LY, _LZ = _LX / _LN, _LY / _LN, _LZ / _LN


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def _mix(c0: tuple[int, int, int], c1: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = _clamp(t, 0.0, 1.0)
    return (
        int(_lerp(c0[0], c1[0], t)),
        int(_lerp(c0[1], c1[1], t)),
        int(_lerp(c0[2], c1[2], t)),
    )


def _ease(t: float) -> float:
    t = _clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _think_color(t: float) -> tuple[int, int, int]:
    """Smooth cycle across _THINK_PALETTE while Atlas is working (~60% faster/stronger)."""
    n = len(_THINK_PALETTE)
    x = (t * 0.58) % n
    i = int(x) % n
    j = (i + 1) % n
    frac = _ease(x - int(x))
    return _mix(_THINK_PALETTE[i], _THINK_PALETTE[j], frac)
