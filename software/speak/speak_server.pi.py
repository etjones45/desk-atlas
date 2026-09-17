#!/usr/bin/env python3
"""Desk Atlas Pi speak server; /face and authenticated /update are fail-safe."""
from __future__ import annotations
import json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
try:
    import face as desk_face
except ImportError:
    desk_face = None
try:
    from desk_update import check_sender_auth, run_update
except ImportError:
    check_sender_auth = lambda headers: False
    run_update = None
FACE_STATES = ("idle", "talk", "listen", "think", "done")
class Handler(BaseHTTPRequestHandler):
    def _json(self, code, value):
        raw=json.dumps(value).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0")); raw=self.rfile.read(n) if n else b"{}"
        try: body=json.loads(raw.decode())
        except Exception: self._json(400,{"ok":False,"error":"invalid json"}); return
        if self.path=="/face":
            state=str(body.get("state","")).lower()
            if state not in FACE_STATES: self._json(400,{"ok":False,"error":"state required"}); return
            if desk_face:
                try: desk_face.set_state(state)
                except Exception: pass
            self._json(200,{"ok":True,"state":state}); return
        if self.path=="/update":
            if not check_sender_auth(self.headers): self._json(401,{"ok":False,"error":"unauthorized"}); return
            result=run_update() if run_update else {"ok":False,"error":"desk_update missing"}; self._json(200 if result.get("ok") else 500,result); return
        self._json(404,{"ok":False,"error":"not found"})
if __name__=="__main__":
    if desk_face and callable(getattr(desk_face,"start",None)): desk_face.start()
    ThreadingHTTPServer((os.environ.get("DESK_ATLAS_HOST","127.0.0.1"),int(os.environ.get("DESK_ATLAS_PORT","8787"))),Handler).serve_forever()
