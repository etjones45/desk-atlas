#!/usr/bin/env python3
"""Grok-style matte sphere face for the Whisplay 240x280 panel.

Looks like the reference: full clay-blue ball, two recessed oval holes,
soft studio light, blink that squashes tall ovals into slits.

Animation moods (speak_server drives these):
  idle   — classic blinks + gentle look-around / bounce (no hyper idle)
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


def _rgb565_bytes(img) -> bytes:
    try:
        import numpy as np  # type: ignore

        arr = np.asarray(img, dtype=np.uint16)
        r = (arr[:, :, 0] >> 3) << 11
        g = (arr[:, :, 1] >> 2) << 5
        b = arr[:, :, 2] >> 3
        return (r | g | b).astype(">u2").tobytes()
    except Exception:
        raw = img.tobytes()
        out = bytearray(WIDTH * HEIGHT * 2)
        j = 0
        for i in range(0, len(raw), 3):
            r, g, b = raw[i], raw[i + 1], raw[i + 2]
            v = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            out[j] = (v >> 8) & 0xFF
            out[j + 1] = v & 0xFF
            j += 2
        return bytes(out)


def _grids():
    """Pixel grids, built once."""
    import numpy as np

    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH]
    return xs.astype(np.float32), ys.astype(np.float32)


_XS = _YS = None


def _get_grids():
    global _XS, _YS
    if _XS is None:
        _XS, _YS = _grids()
    return _XS, _YS


def render_sphere(
    color: tuple[int, int, int],
    cx: float,
    cy: float,
    radius: float,
    blink: float,
    yaw: float,
    pitch: float,
    badge: str = "",
    think_spark: bool = False,
    t: float = 0.0,
):
    """Matte sphere + recessed eye holes. blink 0=open, 1=closed slit."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    xs, ys = _get_grids()
    dx = xs - np.float32(cx)
    dy = ys - np.float32(cy)
    r = np.float32(max(radius, 1.0))
    dist2 = dx * dx + dy * dy
    inside = dist2 <= (r * r)
    nz = np.zeros_like(dx)
    nz[inside] = np.sqrt(np.maximum(0.0, 1.0 - dist2[inside] / (r * r)))
    nx = np.zeros_like(dx)
    ny = np.zeros_like(dx)
    nx[inside] = dx[inside] / r
    ny[inside] = dy[inside] / r

    ndotl = nx * _LX + ny * _LY + nz * _LZ
    # Wrap lighting: matte clay, no hard spec coin.
    wrap = np.clip(ndotl * 0.62 + 0.38, 0.16, 1.0)
    wrap *= 0.55 + 0.45 * nz  # rim falloff
    sheen = np.clip(ndotl, 0.0, 1.0) ** 10 * 0.07

    base = np.array(color, dtype=np.float32)
    shade = base * 0.22
    lit = shade + (base - shade) * wrap[..., None]
    lit += sheen[..., None] * 255.0
    rgb = np.clip(lit, 0, 255)

    # Recessed stadium holes. blink: tall capsule → rounded square → slit.
    b = _ease(_clamp(blink, 0.0, 1.0))
    if b < 0.5:
        k = b * 2.0
        eye_w = r * _lerp(0.125, 0.155, k)
        eye_h = r * _lerp(0.355, 0.165, k)
        corner = min(eye_w, eye_h) * _lerp(1.0, 0.72, k)
    else:
        k = (b - 0.5) * 2.0
        eye_w = r * _lerp(0.155, 0.205, k)
        eye_h = r * _lerp(0.165, 0.052, k)
        corner = min(eye_w, eye_h) * _lerp(0.72, 1.0, k)
    gap = r * 0.235
    eye_y = cy + pitch * r * 0.55 - r * 0.02
    centers = (
        (cx - gap + yaw * r * 0.55, eye_y),
        (cx + gap + yaw * r * 0.55, eye_y),
    )

    def _rounded(ex, ey, hw, hh, rad):
        rad = float(max(0.6, min(rad, hw, hh)))
        ax = np.abs(xs - ex) - (hw - rad)
        ay = np.abs(ys - ey) - (hh - rad)
        return (np.maximum(ax, 0.0) ** 2 + np.maximum(ay, 0.0) ** 2) <= (rad * rad)

    hole = np.zeros((HEIGHT, WIDTH), dtype=bool)
    rim = np.zeros((HEIGHT, WIDTH), dtype=bool)
    for ex, ey in centers:
        hole |= _rounded(ex, ey, eye_w, eye_h, corner)
        rim |= _rounded(ex, ey, eye_w + 2.2, eye_h + 2.2, corner + 1.4)
    hole &= inside
    rim = rim & inside & ~hole

    # Cavity: black well, clay lip around the cut.
    well = np.array((8.0, 8.0, 10.0), dtype=np.float32)
    # Lit inner wall — a sliver on the key-light side of each hole.
    inner_lit = np.zeros_like(hole)
    for ex, ey in centers:
        inner_lit |= _rounded(ex - 1.1, ey - 0.9, eye_w * 0.78, eye_h * 0.78, corner * 0.78)
    inner_lit &= hole
    rgb[hole] = well
    rgb[inner_lit] = well + np.array(color, dtype=np.float32) * 0.07
    rgb[rim] = np.array(color, dtype=np.float32) * (0.22 + 0.20 * wrap[rim])[..., None]

    # Outside the sphere: dark studio + soft contact shadow.
    out = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
    out[:] = np.array(BG, dtype=np.float32)
    # Contact shadow under the ball (scales with radius for listen depth).
    sh_cy = cy + r * 0.82
    sh_rx = r * 0.78
    sh_ry = r * 0.18
    su = (xs - cx) / max(sh_rx, 1.0)
    sv = (ys - sh_cy) / max(sh_ry, 1.0)
    sh = np.clip(1.0 - (su * su + sv * sv), 0.0, 1.0) ** 1.2
    out -= sh[..., None] * 22.0

    out[inside] = rgb[inside]
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")

    # think_spark disabled — Ethan asked to remove the orbiting white dot.
    if False and think_spark:
        pass

    if badge:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((8, HEIGHT - 18), badge[:8], fill=(255, 220, 220), font=font)
    return img


class Face:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state = "idle"
        self._error_code = ""
        self._started = time.monotonic()
        self._blink_t0 = 0.0
        self._blink_dur = 0.22
        self._double_pending = False
        self._triple_pending = False
        self._next_blink = self._started + 1.0
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._board = None
        self._color_now = COLORS["idle"]
        self._scale = 1.0
        self._lean = 0.0
        self._done_until = 0.0
        self._last_led = (-1, -1, -1)
        self._look_yaw = 0.0
        self._look_pitch = 0.0
        self._look_until = 0.0
        self._next_look = self._started + 0.8
        self._bob_burst_until = 0.0
        self._preview_path = os.environ.get("DESK_ATLAS_FACE_PREVIEW", "").strip()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "face": self._state,
                "error_code": self._error_code,
                "size": f"{WIDTH}x{HEIGHT}",
                "board": self._board is not None,
            }

    def set_state(self, state: str, error_code: str = "") -> str:
        s = (state or "idle").strip().lower()
        if s not in STATES:
            s = "idle"
        with self._lock:
            self._state = s
            self._error_code = (error_code or "").upper()
            now = time.monotonic()
            if s == "listen":
                # Quick double-blink so Ethan sees "I heard you"
                self._blink_t0 = now
                self._blink_dur = 0.14
                self._double_pending = True
                self._triple_pending = False
                self._look_yaw = 0.0
                self._look_pitch = -0.08  # eyes lock toward user
                self._look_until = now + 1.4
            elif s == "talk":
                self._look_yaw = 0.0
                self._look_pitch = -0.03
                self._look_until = now + 0.6
            elif s == "done":
                # Punchy acknowledgment blink
                self._blink_t0 = now
                self._blink_dur = 0.15
                self._double_pending = True
                self._triple_pending = False
            elif s == "error":
                self._look_yaw = 0.0
                self._look_pitch = 0.06
                self._look_until = now + 0.8
            if s == "done":
                self._done_until = now + DONE_HOLD_SEC
            else:
                self._done_until = 0.0
            return s

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._open_board()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="desk-face", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def render_still(self, state: str, error_code: str = "", path: str = "", blink: float = 0.0) -> str:
        applied = self.set_state(state, error_code)
        seeds = {
            "idle": 1.15,
            "listen": 0.4,
            "think": 2.2,
            "talk": 0.9,
            "done": 0.6,
            "error": 0.0,
        }
        self._started = time.monotonic() - seeds.get(applied, 1.0)
        self._color_now = COLORS[applied]
        self._scale = (
            1.22
            if applied == "listen"
            else 1.05
            if applied == "talk"
            else 1.08
            if applied == "think"
            else 1.0
        )
        self._lean = 14.0 if applied == "listen" else 3.0 if applied == "think" else 0.0
        self._blink_t0 = 0.0
        self._done_until = 0.0
        dest = path or self._preview_path
        prev = self._preview_path
        if dest:
            self._preview_path = dest
        self._render(force_blink=blink)
        self._preview_path = prev
        return dest

    def _open_board(self) -> None:
        if os.environ.get("DESK_ATLAS_FACE", "1").strip() in ("0", "off", "no"):
            return
        try:
            sys.path.append(os.path.abspath(os.path.expanduser("~/Whisplay/runtime")))
            sys.path.append("/home/orangepi/Whisplay/runtime")
            from whisplay import WhisplayBoard  # type: ignore

            board = WhisplayBoard()
            try:
                board.set_backlight(50)
            except Exception:
                pass
            self._board = board
        except Exception:
            self._board = None

    def _loop(self) -> None:
        interval = 1.0 / max(FPS, 4.0)
        while not self._stop.wait(interval):
            try:
                frame = self._render()
                self._push(frame)
            except Exception:
                pass

    def _maybe_idle_from_done(self, now: float) -> str:
        with self._lock:
            if self._state == "done" and self._done_until and now >= self._done_until:
                self._state = "idle"
                self._error_code = ""
                self._done_until = 0.0
            return self._state

    def _schedule_idle_look(self, now: float) -> None:
        """Gentle look-around — closer to classic idle, a little more life."""
        if now < self._next_look:
            return
        self._look_yaw = random.uniform(-0.12, 0.12)
        self._look_pitch = random.uniform(-0.06, 0.06)
        self._look_until = now + 0.45 + random.random() * 0.7
        self._next_look = self._look_until + 0.8 + random.random() * 1.6
        # Rare soft bob (not constant hyperactivity)
        if random.random() < 0.22:
            self._bob_burst_until = now + 0.35 + random.random() * 0.25

    def _blink_amount(self, now: float, state: str) -> float:
        """0 open … 1 closed. One down-up cycle, optional double/triple."""
        if state == "error":
            return 0.0
        if self._blink_t0 and now >= self._blink_t0:
            u = (now - self._blink_t0) / max(self._blink_dur, 0.05)
            if u >= 1.0:
                if self._triple_pending:
                    self._triple_pending = False
                    self._double_pending = True
                    self._blink_t0 = now + 0.045
                    self._blink_dur = 0.13
                    return 0.0
                if self._double_pending:
                    self._double_pending = False
                    self._blink_t0 = now + 0.05
                    self._blink_dur = 0.14
                    return 0.0
                self._blink_t0 = 0.0
                return 0.0
            if u < 0.45:
                return _ease(u / 0.45)
            return _ease(1.0 - (u - 0.45) / 0.55)
        if now >= self._next_blink:
            self._blink_t0 = now
            if state == "idle":
                # Classic idle + a little more blink/roll (not the hyper pack)
                self._blink_dur = 0.17 + random.random() * 0.08
                gap = 0.65 + random.random() * 1.15
                roll = random.random()
                self._double_pending = roll < 0.50
                self._triple_pending = roll < 0.12
                if random.random() < 0.40:
                    self._look_yaw = random.uniform(-0.12, 0.12)
                    self._look_pitch = random.uniform(-0.06, 0.06)
                    self._look_until = now + 0.45 + random.random() * 0.7
            elif state == "listen":
                self._blink_dur = 0.14
                gap = 1.2 + random.random() * 0.8
                self._double_pending = random.random() < 0.40
                self._triple_pending = False
            elif state == "think":
                self._blink_dur = 0.14
                gap = 0.55 + random.random() * 0.55
                self._double_pending = random.random() < 0.55
                self._triple_pending = random.random() < 0.20
            elif state == "talk":
                self._blink_dur = 0.13
                gap = 1.4 + random.random() * 0.9
                self._double_pending = random.random() < 0.22
                self._triple_pending = False
            elif state == "done":
                self._blink_dur = 0.16
                gap = 1.6 + random.random() * 0.8
                self._double_pending = False
                self._triple_pending = False
            else:
                self._blink_dur = 0.20
                gap = 2.4 + random.random() * 1.2
                self._double_pending = False
                self._triple_pending = False
            self._next_blink = now + gap
        return 0.0

    def _sync_led(self, state: str, rgb: tuple[int, int, int] | None = None) -> None:
        if self._board is None:
            return
        color = rgb if rgb is not None else LED.get(state, LED["idle"])
        color = (color[0] & ~3, color[1] & ~3, color[2] & ~3)
        if color == self._last_led:
            return
        try:
            self._board.set_rgb(*color)
            self._last_led = color
        except Exception:
            pass

    def _render(self, force_blink: float | None = None) -> bytes:
        now = time.monotonic()
        state = self._maybe_idle_from_done(now)
        with self._lock:
            err = self._error_code

        t = now - self._started
        if state == "think":
            target = _think_color(t)
            color_speed = 0.55  # punchier think color shifts
        elif state == "listen":
            target = COLORS["listen"]
            color_speed = 0.55  # snap to cyan fast so wake is obvious
        elif state == "talk":
            target = COLORS["talk"]
            color_speed = 0.28
        elif state == "done":
            target = COLORS["done"]
            color_speed = 0.40
        elif state == "error":
            target = COLORS["error"]
            color_speed = 0.50
        else:
            target = COLORS[state]
            color_speed = 0.22
        self._color_now = _mix(self._color_now, target, color_speed)

        want_scale = 1.0
        want_lean = 0.0
        if state == "listen":
            # Depth: roll/zoom toward user
            want_scale = 1.24
            want_lean = 15.0
        elif state == "think":
            want_scale = 1.12 + 0.03 * math.sin(t * 2.8)
            want_lean = 5.0
        elif state == "talk":
            # Conversational scale pulse (gentle, not frantic)
            want_scale = 1.04 + 0.025 * math.sin(t * 6.2)
        elif state == "idle":
            # Subtle breathing scale
            want_scale = 1.0 + 0.012 * math.sin(t * 1.1)  # soft breathe
        elif state == "done":
            want_scale = 1.06
            want_lean = -2.0  # slight proud lift
        elif state == "error":
            want_scale = 1.02
        self._scale = _lerp(self._scale, want_scale, 0.22)
        self._lean = _lerp(self._lean, want_lean, 0.22)

        blink = self._blink_amount(now, state) if force_blink is None else force_blink

        if state == "idle":
            self._schedule_idle_look(now)

        if self._look_until and now >= self._look_until:
            self._look_yaw = _lerp(self._look_yaw, 0.0, 0.28)
            self._look_pitch = _lerp(self._look_pitch, 0.0, 0.28)
            if abs(self._look_yaw) < 0.01 and abs(self._look_pitch) < 0.01:
                self._look_yaw = 0.0
                self._look_pitch = 0.0
                self._look_until = 0.0

        if state == "error":
            # Punchy micro-shake instead of frozen
            amp, freq = 2.8, 7.5
        elif state == "think":
            # Stronger restless bob — emotion without the white orbiting spark
            amp, freq = 11.0, 2.35
        elif state == "listen":
            amp, freq = 2.4, 1.05
        elif state == "done":
            amp, freq = 2.8, 0.85
        elif state == "talk":
            amp, freq = 2.0, 1.85
        else:
            # idle — classic bob + modest bounce (not hyper)
            amp, freq = 5.8, 1.0

        yaw = math.sin(t * freq) * (0.07 if amp else 0.0)
        pitch = math.cos(t * (freq + 0.22)) * (0.04 if amp else 0.0)
        if state == "idle":
            yaw += math.sin(t * 1.7) * 0.04 + self._look_yaw
            pitch += math.cos(t * 1.15) * 0.028 + self._look_pitch
        elif state == "think":
            # Restless eyes — scanning while working (no spark)
            yaw += math.sin(t * 3.4) * 0.11 + math.sin(t * 1.55) * 0.055
            pitch += math.cos(t * 2.8) * 0.085 + math.cos(t * 1.25) * 0.04
        elif state == "listen":
            # Attentive lock toward user with tiny attentive tremor
            yaw += self._look_yaw + math.sin(t * 3.8) * 0.012
            pitch += self._look_pitch - 0.035 + math.cos(t * 2.9) * 0.01
        elif state == "talk":
            # Warm engaging eye motion — soft gaze wander
            yaw += math.sin(t * 1.55) * 0.045 + math.sin(t * 0.7) * 0.02
            pitch += math.cos(t * 1.25) * 0.032 + self._look_pitch
        elif state == "done":
            yaw += math.sin(t * 1.2) * 0.02
            pitch += -0.02 + math.cos(t * 0.9) * 0.015
        elif state == "error":
            yaw += math.sin(t * freq) * 0.04
            pitch += self._look_pitch

        dx = math.sin(t * freq) * amp if freq else 0.0
        dy = (math.cos(t * (freq + 0.2)) * (amp * 0.40) if freq else 0.0) + self._lean
        if state == "talk":
            # Conversational speaking bob (synced-ish pulse)
            dy += math.sin(t * 6.8) * 2.0 + math.sin(t * 3.4) * 0.7
            dx += math.sin(t * 2.1) * 0.9
        elif state == "idle":
            dx += math.sin(t * 0.55) * 2.8 + math.sin(t * 1.9) * 1.1
            dy += math.cos(t * 0.48) * 1.9 + math.sin(t * 1.55) * 0.9
            if now < self._bob_burst_until:
                dy += math.sin(t * 9.0) * 2.4
                dx += math.cos(t * 7.5) * 1.2
        elif state == "think":
            dx += math.sin(t * 2.7) * 2.2
            dy += math.cos(t * 2.1) * 1.8 + math.sin(t * 4.0) * 1.1
        elif state == "listen":
            # Subtle forward bob while "rolling" toward user
            dy += math.sin(t * 2.2) * 1.1
            # Slight squash feel via vertical compress during lean settle
            dx *= 0.55
        elif state == "done":
            dy += math.sin(t * 3.5) * 1.2
        elif state == "error":
            dx = math.sin(t * freq) * amp
            dy = self._lean + math.cos(t * (freq * 1.3)) * (amp * 0.25)

        cx = WIDTH / 2 + dx
        cy = HEIGHT / 2 + 6 + dy
        # Base radius; listen scale reads as zoom/depth
        radius = min(WIDTH, HEIGHT) * 0.40 * self._scale
        # Subtle squash when leaning forward (listen) or bouncing (talk/idle burst)
        if state == "listen":
            radius *= 1.0 + 0.02 * math.sin(t * 2.0)  # slight breathe while forward
        elif state == "talk":
            radius *= 1.0 + 0.012 * math.sin(t * 6.8)

        led_rgb = None
        if state in ("think", "listen"):
            led_rgb = (
                int(_clamp(self._color_now[0] * 0.85, 0, 255)),
                int(_clamp(self._color_now[1] * 0.85, 0, 255)),
                int(_clamp(self._color_now[2] * 0.95, 0, 255)),
            )
        self._sync_led(state, led_rgb)
        try:
            img = render_sphere(
                self._color_now,
                cx,
                cy,
                radius,
                blink,
                yaw,
                pitch,
                err if state == "error" else "",
                think_spark=False,  # Ethan: no orbiting white dot
                t=t,
            )
        except Exception:
            return b""

        if self._preview_path:
            try:
                img.save(self._preview_path)
            except Exception:
                pass
        return img.tobytes()

    def _push(self, raw: bytes) -> None:
        if not raw or self._board is None:
            return
        try:
            from PIL import Image

            img = Image.frombytes("RGB", (WIDTH, HEIGHT), raw)
            pix = _rgb565_bytes(img)
            self._board.draw_image(0, 0, WIDTH, HEIGHT, pix)
        except Exception:
            return


FACE = Face()


def set_state(state: str, error_code: str = "") -> str:
    return FACE.set_state(state, error_code)


def start() -> None:
    FACE.start()


def snapshot() -> dict:
    return FACE.snapshot()


def main() -> None:
    if "--stills" in sys.argv:
        here = os.path.dirname(os.path.abspath(__file__))
        shots = [
            ("idle", 0.0),
            ("listen", 0.0),
            ("think", 0.0),
            ("talk", 0.0),
            ("done", 0.0),
            ("error", 0.0),
        ]
        for s, b in shots:
            path = os.path.join(here, f"face-preview-{s}.png")
            FACE.render_still(s, "NET" if s == "error" else "", path, blink=b)
            print(path, flush=True)
        # Extra blink frames so we can judge the squash against the video.
        for name, b in (("blink-mid", 0.55), ("blink-shut", 1.0)):
            path = os.path.join(here, f"face-preview-{name}.png")
            FACE.render_still("idle", "", path, blink=b)
            print(path, flush=True)
        return
    start()
    order = ["idle", "listen", "think", "talk", "done", "error"]
    print("face demo — cycling", order, flush=True)
    try:
        while True:
            for s in order:
                set_state(s, "NET" if s == "error" else "")
                print({"face": s}, flush=True)
                time.sleep(3.0)
    except KeyboardInterrupt:
        FACE.stop()


if __name__ == "__main__":
    main()
