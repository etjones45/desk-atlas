#!/usr/bin/env python3
"""Grok-style matte sphere face for WhisPlay; speech failure never depends on it."""
from __future__ import annotations
import os, threading, time
WIDTH=int(os.environ.get("DESK_ATLAS_FACE_W","240")); HEIGHT=int(os.environ.get("DESK_ATLAS_FACE_H","280"))
STATES=("idle","listen","think","talk","done","error")
COLORS={"idle":(28,92,228),"listen":(36,108,240),"think":(228,232,238),"talk":(28,92,228),"done":(28,168,78),"error":(196,36,36)}
class Face:
    def __init__(self): self._state="idle"; self._lock=threading.Lock(); self._board=None; self._thread=None; self._stop=threading.Event()
    def snapshot(self):
        with self._lock: return {"face":self._state,"size":f"{WIDTH}x{HEIGHT}","board":self._board is not None}
    def set_state(self,state,error_code=""):
        with self._lock: self._state=state if state in STATES else "idle"
        return self._state
    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._thread=threading.Thread(target=self._loop,name="desk-face",daemon=True); self._thread.start()
    def stop(self): self._stop.set()
    def _loop(self):
        while not self._stop.wait(1/12): pass
    def render_still(self,state,error_code="",path="",blink=0.0):
        self.set_state(state,error_code)
        try:
            from PIL import Image,ImageDraw
            img=Image.new("RGB",(WIDTH,HEIGHT),(18,18,20)); d=ImageDraw.Draw(img); r=min(WIDTH,HEIGHT)*.4; cx,cy=WIDTH/2,HEIGHT/2+6
            d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=COLORS.get(state,COLORS["idle"]))
            eye_h=r*(.05 if blink>=.9 else .35); eye_w=r*.13
            for ex in (cx-r*.235,cx+r*.235): d.rounded_rectangle((ex-eye_w,cy-eye_h,ex+eye_w,cy+eye_h),radius=max(2,eye_h),fill=(8,8,10))
            if path: img.save(path)
        except Exception: pass
        return path
FACE=Face()
def set_state(state,error_code=""): return FACE.set_state(state,error_code)
def start(): return FACE.start()
def snapshot(): return FACE.snapshot()
if __name__=="__main__": FACE.start(); time.sleep(1)
