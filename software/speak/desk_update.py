#!/usr/bin/env python3
"""Authenticated, non-clobbering OTA update helper for Desk Atlas."""
from __future__ import annotations
import os, subprocess
from pathlib import Path
LIVE=Path(os.environ.get("DESK_ATLAS_LIVE",str(Path.home()/"desk-atlas"))).expanduser()
UPSTREAM=Path(os.environ.get("DESK_ATLAS_UPSTREAM",str(Path.home()/"desk-atlas-upstream"))).expanduser()
PULL_BIN=Path(os.environ.get("DESK_ATLAS_PULL",str(Path.home()/"bin"/"desk-atlas-pull"))).expanduser()
def check_sender_auth(headers):
    expected=(os.environ.get("ATLAS_SENDER_KEY") or "").strip()
    if not expected: return False
    name=(os.environ.get("ATLAS_SENDER_HEADER") or "Authorization").strip() or "Authorization"
    got=(headers.get(name) or "").strip()
    if name.lower()=="authorization": return got in (expected,"Bearer "+expected)
    return got==expected
def _run(cmd,cwd=None):
    try:
        p=subprocess.run(cmd,cwd=str(cwd) if cwd else None,capture_output=True,text=True,timeout=180,check=False)
        return {"ok":p.returncode==0,"code":p.returncode,"stdout":p.stdout[-1000:],"stderr":p.stderr[-1000:]}
    except Exception as e: return {"ok":False,"error":str(e)}
def pull_upstream():
    if PULL_BIN.is_file() and os.access(PULL_BIN,os.X_OK): return _run([str(PULL_BIN)])
    if not (UPSTREAM/".git").is_dir(): return {"ok":False,"error":"no upstream clone and no pull helper"}
    return _run(["git","pull","--ff-only"],UPSTREAM)
def sync_mapped():
    if not UPSTREAM.is_dir() or not LIVE.is_dir(): return {"ok":False,"error":"upstream or live missing"}
    copied=[]
    for src_name,dst_name in (("software/speak/desk_update.py","desk_update.py"),("software/speak/face.py","face.py"),("software/ears/ears.py","ears.py")):
        src=UPSTREAM/src_name; dst=LIVE/dst_name
        if not src.is_file(): continue
        if dst_name=="ears.py" and "--listen" not in src.read_text(errors="replace"):
            continue
        dst.write_bytes(src.read_bytes()); copied.append(dst_name)
    return {"ok":True,"copied":copied,"env_present":(LIVE/".env").is_file()}
def run_update():
    pulled=pull_upstream()
    if not pulled.get("ok"): return {"ok":False,"error":"pull failed","pulled":pulled,"restarted":False,"spoke":False}
    synced=sync_mapped()
    if not synced.get("ok"): return {"ok":False,"error":"sync failed","sync":synced,"restarted":False,"spoke":False}
    return {"ok":True,"pulled":True,"sync":synced,"restarted":False,"spoke":False}
