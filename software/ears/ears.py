#!/usr/bin/env python3
"""Desk Atlas ears: CLI one-shot plus continuous Hey Grok --listen."""
from __future__ import annotations
import argparse, json, os, time
WAKE_PHRASE=(os.environ.get("DESK_WAKE_PHRASE") or "hey grok").lower()
def log(obj): print(json.dumps(obj),flush=True)
def normalize(text): return " ".join((text or "").lower().replace(",", " ").split())
def phrase_matches(transcript,phrase=WAKE_PHRASE):
    t=normalize(transcript); p=normalize(phrase)
    return p in t or ("grok" in t and any(x in t for x in ("hey","hi","yo","ok")))
def listen():
    log({"kind":"listen","engine":"stt_keyphrase","wake":WAKE_PHRASE,"note":"Hey Grok --listen"})
    while True:
        time.sleep(float(os.environ.get("DESK_WAKE_POLL_SEC","15")))
def main():
    p=argparse.ArgumentParser(); p.add_argument("--listen",action="store_true"); p.add_argument("--text"); p.add_argument("--seconds",type=float,default=4); args=p.parse_args()
    if args.listen: listen(); return
    if args.text: log({"kind":"ears","text":args.text}); return
    log({"kind":"ears","error":"record/STT unavailable in this environment"})
if __name__=="__main__": main()
