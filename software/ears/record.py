#!/usr/bin/env python3
"""Record N seconds of mic audio to WAV for Desk Atlas ears.

Prefer arecord (Orange Pi / WhisPlay). Fall back to ffmpeg avfoundation (Mac)
or alsa (Linux).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


class RecordError(RuntimeError):
    pass


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


def record_wav(seconds: float, out: Path) -> Path:
    """Record `seconds` of mono 16 kHz WAV to `out`. Returns out path."""
    if seconds <= 0:
        raise RecordError("seconds must be > 0")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if which("arecord"):
        _arecord(seconds, out)
        return out
    if which("ffmpeg"):
        _ffmpeg(seconds, out)
        return out
    raise RecordError("neither arecord nor ffmpeg found on PATH")


def _arecord(seconds: float, out: Path) -> None:
    # WhisPlay / ALSA default device; override with ATLAS_RECORD_DEVICE
    device = os.environ.get("ATLAS_RECORD_DEVICE", "default")
    cmd = [
        "arecord",
        "-D",
        device,
        "-f",
        "S16_LE",
        "-r",
        "16000",
        "-c",
        "1",
        "-d",
        str(max(1, int(round(seconds)))),
        str(out),
    ]
    print(f"recording {seconds}s via arecord ({device})…", file=sys.stderr)
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RecordError(f"arecord failed (exit {e.returncode})") from e


def _ffmpeg(seconds: float, out: Path) -> None:
    device = os.environ.get("ATLAS_RECORD_DEVICE")
    # Detect platform input: Mac avfoundation vs Linux alsa
    if sys.platform == "darwin":
        # default mic index ":0" or env override like "none:0" / ":1"
        inp = device or ":0"
        fmt = "avfoundation"
    else:
        inp = device or "default"
        fmt = "alsa"

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        fmt,
        "-i",
        inp,
        "-t",
        str(seconds),
        "-ar",
        "16000",
        "-ac",
        "1",
        str(out),
    ]
    print(f"recording {seconds}s via ffmpeg ({fmt}:{inp})…", file=sys.stderr)
    try:
        subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        raise RecordError(f"ffmpeg record failed (exit {e.returncode})") from e
