#!/usr/bin/env python3
"""Desk Atlas face — Pi live name is face.py (~/desk-atlas/face.py).

Public API used by speak_server:
    face.start(); face.set_state("talk"); face.snapshot()

The full object-space clay-sphere rig is the animation-chat standard
(artifacts/desk-atlas/face.py). This module stays import-safe so an OTA
pull cannot kill speech if the large body has not landed yet.
No API keys live here. TTS / webhook / OTA keys stay in ~/desk-atlas/.env.
"""
from __future__ import annotations

import os
import threading

WIDTH = int(os.environ.get("DESK_ATLAS_FACE_W", "240"))
HEIGHT = int(os.environ.get("DESK_ATLAS_FACE_H", "280"))
FPS = float(os.environ.get("DESK_ATLAS_FACE_FPS", "24"))

STATES = (
    "idle", "listen", "think", "talk", "done",
    "happy", "error", "sad", "sleep", "surprise",
)
_ALIAS = {
    "speak": "talk", "speaking": "talk", "ok": "done", "success": "done",
    "fail": "error", "thinking": "think", "listening": "listen",
    "sleepy": "sleep", "wake": "surprise", "smile": "happy",
}

class Face:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = "idle"
        self._error_code = ""
        self._board = None

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "face": self._state,
                "error_code": self._error_code,
                "size": f"{WIDTH}x{HEIGHT}",
                "board": self._board is not None,
                "fps": FPS,
                "numpy": False,
                "rig": "shim",
            }

    def set_state(self, state: str, error_code: str = "") -> str:
        s = (state or "idle").strip().lower()
        s = _ALIAS.get(s, s)
        if s not in STATES:
            s = "idle"
        with self._lock:
            self._state = s
            self._error_code = (error_code or "").upper()
        return s

    def start(self) -> None:
        return

    def stop(self) -> None:
        return

FACE = Face()

def set_state(state: str, error_code: str = "") -> str:
    return FACE.set_state(state, error_code)

def start() -> None:
    FACE.start()

def snapshot() -> dict:
    return FACE.snapshot()
