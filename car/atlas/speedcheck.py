"""Internet speed test from the Pi (what the Starlink is giving the car right now).

Uses Cloudflare's public speed-test endpoints. Two sizes:
  light: about 25 MB of data  (the automatic daily test)
  full:  about 75 MB of data  (when you tap "Run speed test" in the app)
The result is the speed the Pi itself gets over its WiFi link to the Starlink, so phones
sitting closer to the dish can see a bit more.
"""
from __future__ import annotations

import http.client
import os
import socket
import ssl
import threading
import time

HOST = os.environ.get("CAR_ATLAS_SPEED_HOST", "speed.cloudflare.com")
PLAIN = os.environ.get("CAR_ATLAS_SPEED_PLAIN") == "1"       # tests only
PROFILES = {
    "light": {"down_mb": 18, "down_s": 5.0, "up_mb": 5, "up_s": 4.0, "streams": 2},
    "full": {"down_mb": 60, "down_s": 8.0, "up_mb": 14, "up_s": 6.0, "streams": 3},
}


def _conn(timeout: float = 10.0):
    if PLAIN:
        host, _, port = HOST.partition(":")
        return http.client.HTTPConnection(host, int(port or 80), timeout=timeout)
    return http.client.HTTPSConnection(HOST, 443, timeout=timeout, context=ssl.create_default_context())


def _headers() -> dict:
    return {"User-Agent": "car-atlas-pi", "Accept": "*/*"}


def measure_ping(samples: int = 6) -> tuple[float | None, float | None, str | None]:
    """Round-trip time for a tiny request on an already-open connection. Returns (ms, jitter_ms, where)."""
    times, where = [], None
    try:
        c = _conn(6)
        for i in range(samples + 1):
            t0 = time.perf_counter()
            c.request("GET", "/__down?bytes=0", headers=_headers())
            r = c.getresponse()
            r.read()
            dt = (time.perf_counter() - t0) * 1000
            if i:                       # the first one includes the connection setup
                times.append(dt)
            where = where or r.getheader("cf-meta-colo") or (r.getheader("cf-ray") or "").rpartition("-")[2] or None
        c.close()
    except Exception:  # noqa: BLE001
        pass
    if not times:
        return None, None, where
    times.sort()
    best = times[0]
    jitter = sum(abs(t - best) for t in times) / len(times)
    return round(best, 1), round(jitter, 1), where


def _down_worker(total: list, lock: threading.Lock, stop: threading.Event, cap_bytes: int, errors: list) -> None:
    try:
        c = _conn(10)
        c.request("GET", f"/__down?bytes={cap_bytes}", headers=_headers())
        r = c.getresponse()
        if r.status != 200:
            errors.append(f"download HTTP {r.status}")
            return
        while not stop.is_set():
            chunk = r.read(65536)
            if not chunk:
                break
            with lock:
                total[0] += len(chunk)
        c.close()
    except Exception as e:  # noqa: BLE001
        errors.append(str(e)[:80])


def _up_worker(total: list, lock: threading.Lock, stop: threading.Event, cap_bytes: int, errors: list) -> None:
    block = os.urandom(32768)
    try:
        c = _conn(10)
        c.connect()
        try:                             # small send buffer, so "sent" means "actually left the Pi"
            c.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)
        except OSError:
            pass
        c.putrequest("POST", "/__up")
        c.putheader("User-Agent", "car-atlas-pi")
        c.putheader("Content-Type", "application/octet-stream")
        c.putheader("Content-Length", str(cap_bytes))
        c.endheaders()
        sent = 0
        while sent < cap_bytes and not stop.is_set():
            n = min(len(block), cap_bytes - sent)
            c.send(block[:n])
            sent += n
            with lock:
                total[0] += n
        c.close()                        # we only care how fast it left; no need to wait for the reply
    except Exception as e:  # noqa: BLE001
        errors.append(str(e)[:80])


def _throughput(worker, cap_mb: int, seconds: float, streams: int) -> tuple[float | None, int, list]:
    total, lock, stop, errors = [0], threading.Lock(), threading.Event(), []
    per_stream = int(cap_mb * 1_000_000 / streams)
    threads = [threading.Thread(target=worker, args=(total, lock, stop, per_stream, errors), daemon=True)
               for _ in range(streams)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    # Skip the first moments (connection setup + ramp-up) when working out the speed.
    warm_t, warm_b = None, 0
    while time.perf_counter() - t0 < seconds and any(t.is_alive() for t in threads):
        time.sleep(0.1)
        if warm_t is None and time.perf_counter() - t0 >= 0.8 and total[0] > 0:
            warm_t, warm_b = time.perf_counter(), total[0]
    stop.set()
    end_t, end_b = time.perf_counter(), total[0]
    for t in threads:
        t.join(timeout=2)
    if end_b <= 0:
        return None, 0, errors
    if warm_t is not None and end_t - warm_t > 0.5 and end_b > warm_b:
        mbps = (end_b - warm_b) * 8 / (end_t - warm_t) / 1e6
    else:
        mbps = end_b * 8 / max(end_t - t0, 0.05) / 1e6
    return round(mbps, 1), end_b, errors


def run_test(profile: str = "light") -> dict:
    p = PROFILES.get(profile, PROFILES["light"])
    started = time.time()
    ping, jitter, where = measure_ping()
    if ping is None:
        return {"ok": False, "at": started, "profile": profile, "error": "Couldn't reach the speed test server."}
    down, down_b, e1 = _throughput(_down_worker, p["down_mb"], p["down_s"], p["streams"])
    up, up_b, e2 = _throughput(_up_worker, p["up_mb"], p["up_s"], max(1, p["streams"] - 1))
    ok = down is not None
    return {
        "ok": ok, "at": started, "profile": profile,
        "ping_ms": ping, "jitter_ms": jitter, "down_mbps": down, "up_mbps": up,
        "used_mb": round((down_b + up_b) / 1e6, 1), "server": where,
        "took_s": round(time.time() - started, 1),
        "error": None if ok else (e1 or e2 or ["no data"])[0],
    }


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(run_test(sys.argv[1] if len(sys.argv) > 1 else "light"), indent=1))
