#!/usr/bin/env python3
"""Desk Atlas ears — CLI one-shot + continuous --listen (Hey Grok).

CLI:
  python3 ears.py --seconds 4
  python3 ears.py --wav file.wav
  python3 ears.py --text "smoke"

Listen (systemd):
  python3 ears.py --listen

Wake:
  Prefer openwakeword when models/hey_grok.onnx (or DESK_WAKE_MODEL) exists.
  Else STT keyphrase interim: energy gate → short STT → fuzzy match
  DESK_WAKE_PHRASE (default "hey grok").

On wake → face.set_state("listen") (import face or POST :8787/face),
then record → STT → webhook.

JSON logs: {"kind":"listen","wake":"hey grok",...}
Never prints secrets.
"""

from __future__ import annotations

import argparse
import array
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if (HERE / "ears").is_dir() and str(HERE / "ears") not in sys.path:
    sys.path.insert(0, str(HERE / "ears"))

from record import RecordError, record_wav  # noqa: E402
from stt_xai import SttError, stt_file  # noqa: E402
from webhook import WebhookError, post_voice_in  # noqa: E402

BASE = HERE if (HERE / "face.py").is_file() or (HERE / ".env").is_file() else HERE.parent
DROPBOX = Path(os.environ.get("ATLAS_DROPBOX") or (BASE / "dropbox"))
WAKE_PHRASE = (os.environ.get("DESK_WAKE_PHRASE") or "hey grok").strip().lower() or "hey grok"
FACE_URL = (os.environ.get("DESK_FACE_URL") or "http://127.0.0.1:8787/face").strip()


def log(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except OSError:
        pass


def write_dropbox(text: str, note: str = "", *, source: str = "ears") -> Path:
    DROPBOX.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = DROPBOX / f"note-{ts}.json"
    path.write_text(
        json.dumps(
            {"text": text, "thread": "desk-work", "source": source, "note": note, "ts": ts},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def env_flags() -> dict:
    return {
        "XAI_API_KEY": bool((os.environ.get("XAI_API_KEY") or "").strip()),
        "ATLAS_WEBHOOK_URL": bool((os.environ.get("ATLAS_WEBHOOK_URL") or "").strip()),
        "ATLAS_SENDER_KEY": bool((os.environ.get("ATLAS_SENDER_KEY") or "").strip()),
    }


def set_face_listen() -> None:
    try:
        import face as desk_face  # type: ignore

        fn = getattr(desk_face, "set_state", None)
        if callable(fn):
            fn("listen")
            log({"kind": "face", "state": "listen", "via": "import"})
            return
    except Exception as e:
        log({"kind": "face", "warn": f"import:{e}"})
    try:
        req = urllib.request.Request(
            FACE_URL,
            data=json.dumps({"state": "listen"}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            log({"kind": "face", "state": "listen", "via": "http", "status": int(resp.status)})
    except Exception as e:
        log({"kind": "face", "error": str(e)})


def normalize(text: str) -> str:
    t = (text or "").lower()
    t = t.replace("hey,", "hey ").replace("hey, ", "hey ")
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for bad, good in (("groc", "grok"), ("grock", "grok"), ("greg", "grok")):
        t = t.replace(bad, good)
    return t


def phrase_matches(transcript: str, phrase: str = WAKE_PHRASE) -> bool:
    t = normalize(transcript)
    p = normalize(phrase)
    if not t:
        return False
    if p in t:
        return True
    if "grok" in t and any(w in t for w in ("hey", "hi", "yo", "ok", "okay")):
        return True
    return t in ("grok", "hey grok", "hi grok", "yo grok")


def resolve_oww_model() -> Path | None:
    env = (os.environ.get("DESK_WAKE_MODEL") or "").strip()
    cands: list[Path] = []
    if env:
        cands.append(Path(env).expanduser())
    cands.extend(
        [
            BASE / "models" / "hey_grok.onnx",
            HERE / "models" / "hey_grok.onnx",
            Path.home() / "desk-atlas" / "models" / "hey_grok.onnx",
        ]
    )
    for c in cands:
        if c.is_file():
            return c
    return None


def record_utterance(seconds: float) -> str:
    tmp = HERE / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    wav = tmp / f"utt-{int(time.time())}.wav"
    try:
        record_wav(seconds, wav)
        return stt_file(wav)
    finally:
        try:
            wav.unlink(missing_ok=True)
        except OSError:
            pass


def rms_s16le(pcm: bytes) -> float:
    if len(pcm) < 2:
        return 0.0
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) - (len(pcm) % 2)])
    if not samples:
        return 0.0
    acc = 0.0
    for s in samples:
        acc += float(s) * float(s)
    return (acc / len(samples)) ** 0.5


def strip_wake(transcript: str) -> str:
    t = normalize(transcript)
    for w in ("hey grok", "hi grok", "yo grok", "ok grok", "okay grok", "grok"):
        t = t.replace(w, " ")
    return re.sub(r"\s+", " ", t).strip()


def post_utterance(text: str) -> None:
    text = (text or "").strip()
    if not text:
        return
    try:
        code, body = post_voice_in(text, thread="desk-work", source="ears-listen")
        log({"kind": "listen", "webhook": code, "body": (body or "")[:200]})
    except WebhookError as e:
        path = write_dropbox(text, note=str(e), source="ears-listen")
        log({"kind": "listen", "webhook_error": str(e), "dropbox": str(path)})


def listen_openwakeword(model_path: Path, utterance_sec: float) -> None:
    import numpy as np
    from openwakeword.model import Model

    oww = Model(wakeword_models=[str(model_path)], inference_framework="onnx")
    log(
        {
            "kind": "listen",
            "engine": "openwakeword",
            "model": str(model_path),
            "wake": WAKE_PHRASE,
            "env": env_flags(),
        }
    )
    rate = 16000
    chunk = 1280
    device = os.environ.get("ATLAS_RECORD_DEVICE", "default")
    threshold = float(os.environ.get("DESK_WAKE_THRESHOLD", "0.5"))
    cmd = [
        "arecord",
        "-D",
        device,
        "-f",
        "S16_LE",
        "-r",
        str(rate),
        "-c",
        "1",
        "-t",
        "raw",
        "-q",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    assert proc.stdout is not None
    try:
        while True:
            raw = proc.stdout.read(chunk * 2)
            if not raw or len(raw) < chunk * 2:
                time.sleep(0.05)
                continue
            audio = np.frombuffer(raw, dtype=np.int16)
            preds = oww.predict(audio)
            score = 0.0
            hit = None
            if isinstance(preds, dict):
                for name, val in preds.items():
                    try:
                        v = float(val)
                    except (TypeError, ValueError):
                        continue
                    if v > score:
                        score, hit = v, name
            if score < threshold:
                continue
            log(
                {
                    "kind": "listen",
                    "wake": WAKE_PHRASE,
                    "engine": "openwakeword",
                    "score": round(score, 3),
                    "model": hit or model_path.name,
                }
            )
            set_face_listen()
            try:
                text = record_utterance(utterance_sec)
            except (RecordError, SttError) as e:
                log({"kind": "listen", "error": "utterance", "detail": str(e)})
                continue
            log({"kind": "listen", "transcript": text})
            post_utterance(text)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except Exception:
            proc.kill()


def listen_stt_keyphrase(utterance_sec: float) -> None:
    rate = 16000
    gate_sec = float(os.environ.get("DESK_WAKE_GATE_SEC", "1.6"))
    energy_threshold = float(os.environ.get("DESK_WAKE_ENERGY", "350"))
    cooldown = float(os.environ.get("DESK_WAKE_COOLDOWN", "1.0"))
    device = os.environ.get("ATLAS_RECORD_DEVICE", "default")
    log(
        {
            "kind": "listen",
            "engine": "stt_keyphrase",
            "wake": WAKE_PHRASE,
            "gate_sec": gate_sec,
            "energy_threshold": energy_threshold,
            "env": env_flags(),
            "note": "no hey_grok.onnx — interim STT wake",
        }
    )
    tmp = HERE / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)

    while True:
        gate_wav = tmp / f"gate-{int(time.time())}.wav"
        cmd = [
            "arecord",
            "-D",
            device,
            "-f",
            "S16_LE",
            "-r",
            str(rate),
            "-c",
            "1",
            "-d",
            str(max(1, int(round(gate_sec)))),
            str(gate_wav),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            log({"kind": "listen", "error": "arecord", "detail": str(e)})
            time.sleep(15)  # whisplay-sound deferred at boot — avoid log spam
            continue

        try:
            data = gate_wav.read_bytes()
            pcm = data[44:] if len(data) > 44 else data
            rms = rms_s16le(pcm)
        except OSError:
            rms = 0.0

        if rms < energy_threshold:
            try:
                gate_wav.unlink(missing_ok=True)
            except OSError:
                pass
            continue

        try:
            gate_text = stt_file(gate_wav)
        except SttError as e:
            log({"kind": "listen", "gate_stt_error": str(e), "rms": round(rms, 1)})
            try:
                gate_wav.unlink(missing_ok=True)
            except OSError:
                pass
            time.sleep(cooldown)
            continue
        finally:
            try:
                gate_wav.unlink(missing_ok=True)
            except OSError:
                pass

        log({"kind": "listen", "gate_transcript": gate_text, "rms": round(rms, 1)})
        if not phrase_matches(gate_text):
            time.sleep(cooldown)
            continue

        log({"kind": "listen", "wake": WAKE_PHRASE, "engine": "stt_keyphrase", "matched": gate_text})
        set_face_listen()
        remainder = strip_wake(gate_text)
        try:
            if len(remainder.split()) >= 2:
                text = remainder
            else:
                text = record_utterance(utterance_sec)
        except (RecordError, SttError) as e:
            log({"kind": "listen", "error": "utterance", "detail": str(e)})
            time.sleep(cooldown)
            continue
        log({"kind": "listen", "transcript": text})
        post_utterance(text)
        time.sleep(cooldown)


def run_oneshot(args: argparse.Namespace) -> int:
    text: str | None = None
    wav_path: Path | None = None
    temp_wav = False
    try:
        if args.text is not None:
            text = args.text.strip()
            if not text:
                print("empty --text", file=sys.stderr)
                return 2
        elif args.wav is not None:
            wav_path = args.wav
            print(f"STT {wav_path}…", file=sys.stderr)
            text = stt_file(wav_path)
        else:
            tmp = HERE / "tmp"
            tmp.mkdir(parents=True, exist_ok=True)
            wav_path = tmp / f"rec-{int(time.time())}.wav"
            temp_wav = not args.keep_wav
            record_wav(args.seconds, wav_path)
            print(f"STT {wav_path}…", file=sys.stderr)
            text = stt_file(wav_path)
    except (RecordError, SttError) as e:
        path = write_dropbox("", note=f"ears failed: {e}", source="ears-error")
        print(f"ERROR: {e}", file=sys.stderr)
        print(f"dropbox note → {path}", file=sys.stderr)
        if temp_wav and wav_path and wav_path.is_file():
            try:
                wav_path.unlink()
            except OSError:
                pass
        return 1

    assert text is not None
    print(f"transcript: {text!r}", file=sys.stderr)
    if args.no_webhook:
        print(text)
        if temp_wav and wav_path and wav_path.is_file():
            try:
                wav_path.unlink()
            except OSError:
                pass
        return 0

    try:
        code, body = post_voice_in(text, thread="desk-work", source="ears")
        print(f"webhook HTTP {code}: {body}", file=sys.stderr)
        if not (200 <= code < 300):
            path = write_dropbox(text, note=f"webhook HTTP {code}: {body}")
            print(f"dropbox fallback → {path}", file=sys.stderr)
            return 1
    except WebhookError as e:
        path = write_dropbox(text, note=str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        print(f"dropbox fallback → {path}", file=sys.stderr)
        return 1
    finally:
        if temp_wav and wav_path and wav_path.is_file():
            try:
                wav_path.unlink()
            except OSError:
                pass
    return 0


def run_listen(args: argparse.Namespace) -> int:
    model = resolve_oww_model()
    utterance_sec = float(args.seconds)
    try:
        if model is not None:
            try:
                listen_openwakeword(model, utterance_sec)
                return 0
            except Exception as e:
                log({"kind": "listen", "oww_fallback": str(e)})
        listen_stt_keyphrase(utterance_sec)
        return 0
    except KeyboardInterrupt:
        log({"kind": "listen", "stop": "keyboard"})
        return 0


def main() -> None:
    load_dotenv(BASE / ".env")
    load_dotenv(HERE / ".env")
    load_dotenv(Path.cwd() / ".env")

    p = argparse.ArgumentParser(description="Desk Atlas ears: record → STT → webhook (+ --listen)")
    p.add_argument("--listen", action="store_true", help="continuous Hey Grok wake loop")
    p.add_argument(
        "--seconds",
        type=float,
        default=4.0,
        metavar="N",
        help="record N seconds (CLI default 4; listen utterance length)",
    )
    p.add_argument("--wav", type=Path, help="transcribe existing WAV/MP3 then webhook")
    p.add_argument("--text", help="send typed text (skip mic/STT) for webhook test")
    p.add_argument("--no-webhook", action="store_true", help="print transcript only")
    p.add_argument("--keep-wav", action="store_true", help="keep temp recording under tmp/")
    args = p.parse_args()

    if args.listen:
        raise SystemExit(run_listen(args))
    raise SystemExit(run_oneshot(args))


if __name__ == "__main__":
    main()
