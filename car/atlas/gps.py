"""Reads a USB GPS receiver (NMEA over a serial port) in the background.

Starlink stopped sharing the dish's GPS with local devices in May 2026, so the coverage map and
"find my car" use a cheap USB GPS (u-blox style, shows up as /dev/ttyACM0 or /dev/ttyUSB0).
Plug it into the Pi's USB1 port. Nothing breaks if there isn't one.
"""
from __future__ import annotations

import glob
import os
import threading
import time


def _checksum_ok(line: str) -> bool:
    if "*" not in line:
        return False
    body, _, cs = line[1:].partition("*")
    calc = 0
    for ch in body:
        calc ^= ord(ch)
    try:
        return calc == int(cs[:2], 16)
    except ValueError:
        return False


def _coord(value: str, hemi: str) -> float | None:
    if not value or "." not in value:
        return None
    dot = value.index(".")
    deg_len = dot - 2
    try:
        deg = float(value[:deg_len])
        minutes = float(value[deg_len:])
    except ValueError:
        return None
    out = deg + minutes / 60
    return -out if hemi in ("S", "W") else out


def parse_nmea(line: str, state: dict) -> bool:
    """Update `state` from one NMEA sentence. Returns True if a position was updated."""
    line = line.strip()
    if not line.startswith("$") or not _checksum_ok(line):
        return False
    f = line[1:].split("*")[0].split(",")
    kind = f[0][2:]  # GPRMC / GNRMC / GPGGA ...
    if kind == "RMC" and len(f) >= 9:
        if f[2] != "A":
            state["fix"] = False
            return False
        lat, lon = _coord(f[3], f[4]), _coord(f[5], f[6])
        if lat is None or lon is None:
            return False
        try:
            knots = float(f[7]) if f[7] else 0.0
        except ValueError:
            knots = 0.0
        try:
            course = float(f[8]) if f[8] else None
        except ValueError:
            course = None
        state.update({"lat": round(lat, 6), "lon": round(lon, 6), "speed_mph": round(knots * 1.15078, 1),
                      "course": course, "fix": True, "at": time.time()})
        return True
    if kind == "GGA" and len(f) >= 10:
        try:
            state["sats"] = int(f[7]) if f[7] else 0
            state["fix_quality"] = int(f[6]) if f[6] else 0
            state["alt_m"] = float(f[9]) if f[9] else None
        except ValueError:
            pass
    return False


def find_device(preferred: str = "auto") -> str | None:
    if preferred and preferred != "auto":
        return preferred if os.path.exists(preferred) else None
    for pattern in ("/dev/serial/by-id/*", "/dev/ttyACM*", "/dev/ttyUSB*"):
        for dev in sorted(glob.glob(pattern)):
            return dev
    return None


class GPSReader(threading.Thread):
    def __init__(self, device: str = "auto"):
        super().__init__(daemon=True)
        self.preferred = device
        self.state: dict = {"device": None, "fix": False}
        self.lock = threading.Lock()

    def snapshot(self) -> dict:
        with self.lock:
            s = dict(self.state)
        s["fresh"] = bool(s.get("fix") and s.get("at") and time.time() - s["at"] < 15)
        return s

    def run(self) -> None:
        while True:
            dev = find_device(self.preferred)
            with self.lock:
                self.state["device"] = dev
            if not dev:
                time.sleep(15)
                continue
            try:
                import serial  # type: ignore
                with serial.Serial(dev, 9600, timeout=2) as port:
                    while True:
                        raw = port.readline()
                        if not raw:
                            continue
                        line = raw.decode("ascii", errors="ignore")
                        with self.lock:
                            parse_nmea(line, self.state)
            except Exception as e:  # noqa: BLE001 - unplugged, permissions, no pyserial...
                with self.lock:
                    self.state.update({"fix": False, "error": str(e)[:120]})
                time.sleep(5)
