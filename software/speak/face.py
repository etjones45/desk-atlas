#!/usr/bin/env python3
"""Grok-style matte sphere face for the Whisplay 240x280 panel.

Public API is unchanged, so speak_server keeps working:
    face.start(); face.set_state(\"talk\"); face.snapshot()

Laptop preview:
    DESK_ATLAS_FACE_PREVIEW=/tmp/desk-atlas-face.png python3 face.py
Pi: same file at ~/desk-atlas/face.py. Face failure never kills speech.
"""
