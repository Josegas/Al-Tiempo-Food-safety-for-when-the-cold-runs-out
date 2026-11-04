"""End-to-end check of the deployed demo (used after every deploy, locally and in CI).

    python scripts/smoke_test.py [--url https://xxxx.cloudfront.net] [--no-reminder]

1. GET  /api/health
2. POST /api/chat   "I cooked beans at 12:00" (demo: 38 °C day, clock 12:00) -> must say 13:00
3. POST /api/chat   asks for a reminder -> polls /api/reminders until it arrives (demo: ~1 min)
Prints latency and reminder delay (numbers for docs/metrics.md). Exit code 1 on failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
import uuid
from pathlib import Path

OUTPUTS = Path(__file__).resolve().parent.parent / "build" / "outputs.json"


def call(url: str, method: str = "GET", body: dict | None = None, timeout: int = 40) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(  # noqa: S310 (our own HTTPS endpoint)
        url, data=data, method=method, headers={"content-type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None)
    ap.add_argument("--no-reminder", action="store_true")
    args = ap.parse_args()
    base = args.url or json.loads(OUTPUTS.read_text())["AlTiempoApp"]["SiteUrl"]
    base = base.rstrip("/")
    session = f"smoke-{uuid.uuid4()}-{int(time.time())}"
    ok = True

    print("1) health:", call(f"{base}/api/health"))

    t0 = time.perf_counter()
    r = call(
        f"{base}/api/chat",
        "POST",
        {"prompt": "I cooked beans at 12:00 and I have no fridge. Until what time can we eat them?",
         "language": "en", "session_id": session, "demo": True},
    )  # fmt: skip
    ms = int((time.perf_counter() - t0) * 1000)
    passed = "13:00" in r.get("answer", "") or "1:00" in r.get("answer", "")
    ok &= passed
    print(f"2) safe window: {'PASS' if passed else 'FAIL'} ({ms} ms) -> {r.get('answer', r)[:160]}")

    if not args.no_reminder:
        r = call(
            f"{base}/api/chat",
            "POST",
            {"prompt": "Please schedule a reminder so we eat them in time.", "language": "en",
             "session_id": session, "demo": True},
        )  # fmt: skip
        print(f"3) reminder requested -> {r.get('answer', r)[:160]}")
        asked = time.time()
        delivered = None
        while time.time() - asked < 180:
            time.sleep(10)
            rem = call(f"{base}/api/reminders?session_id={session}")["reminders"]
            if rem:
                delivered = rem[0]
                break
        passed = delivered is not None
        ok &= passed
        if delivered:
            print(f"   reminder: PASS, arrived {int(time.time() - asked)} s after asking; "
                  f"scheduler delay {delivered.get('delay_s')} s -> {delivered.get('message')}")  # fmt: skip
        else:
            print("   reminder: FAIL (not delivered within 3 minutes)")

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
