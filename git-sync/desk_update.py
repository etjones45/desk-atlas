#!/usr/bin/env python3
"""Non-clobbering OTA sync helper; refuses CLI-only ears overwrite."""
from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path
LIVE=Path(os.environ.get("DESK_ATLAS_LIVE",str(Path.home()/"desk-atlas"))).expanduser()
UPSTREAM=Path(os.environ.get("DESK_ATLAS_UPSTREAM",str(Path.home()/"desk-atlas-upstream"))).expanduser()
PULL_BIN=Path(os.environ.get("DESK_ATLAS_PULL",str(Path.home()/"bin"/"desk-atlas-pull"))).expanduser()
def check_sender_auth(headers):
    key=(os.environ.get("ATLAS_SENDER_KEY") or "").strip(); name=(os.environ.get("ATLAS_SENDER_HEADER") or "Authorization").strip() or "Authorization"; got=(headers.get(name) or "").strip()
    return bool(key and (got==key or (name.lower()=="authorization" and got=="Bearer "+key)))
def pull_upstream():
    if PULL_BIN.is_file() and os.access(PULL_BIN,os.X_OK): return subprocess.run([str(PULL_BIN)],capture_output=True).returncode==0
    if not (UPSTREAM/".git").is_dir(): return False
    return subprocess.run(["git","pull","--ff-only"],cwd=UPSTREAM,capture_output=True).returncode==0
def sync_mapped():
    copied=[]
    for s,d in (("software/speak/desk_update.py","desk_update.py"),("software/speak/face.py","face.py")):
        src=UPSTREAM/s; dst=LIVE/d
        if src.is_file() and LIVE.is_dir(): shutil.copy2(src,dst); copied.append(d)
    src=UPSTREAM/"software/ears/ears.py"
    if src.is_file() and "--listen" in src.read_text(errors="replace"):
        shutil.copy2(src,LIVE/"ears.py"); copied.append("ears.py")
    return {"ok":True,"copied":copied,"ears_policy":"refuse CLI-only overwrite"}
def run_update():
    if not pull_upstream(): return {"ok":False,"error":"pull failed","restarted":False,"spoke":False}
    sync=sync_mapped(); return {"ok":bool(sync.get("ok")),"sync":sync,"restarted":False,"spoke":False}
