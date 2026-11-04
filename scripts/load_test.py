"""Small load test: shows that API Gateway's throttle (10 req/s, burst 20) protects the budget.

    python scripts/load_test.py                 # site from build/outputs.json
    python scripts/load_test.py --site https://xxxx.cloudfront.net

It only calls GET /api/health (Lambda answers {"ok": true}): no model call, no tokens, and it does
not use the daily chat cap. About 400 requests in total cost a fraction of a cent.

Phase 1 "normal use": 8 req/s for 10 s, under the limit -> all should be 200.
Phase 2 "burst": 300 requests at once from 60 threads, far over the limit -> API Gateway answers
429 to the excess, before Lambda or Bedrock are reached.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def hit(url: str) -> tuple[int, float]:
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"user-agent": "al-tiempo-load-test"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (our own HTTPS endpoint)
            resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    except Exception:  # timeout / network
        status = 0
    return status, (time.perf_counter() - t0) * 1000


def summary(name: str, results: list[tuple[int, float]], seconds: float) -> dict:
    codes = Counter(s for s, _ in results)
    ok_ms = sorted(ms for s, ms in results if s == 200)
    row = {
        "phase": name,
        "requests": len(results),
        "seconds": round(seconds, 1),
        "status": dict(sorted(codes.items())),
        "p50_ms_200": int(statistics.median(ok_ms)) if ok_ms else None,
        "p95_ms_200": int(ok_ms[int(len(ok_ms) * 0.95) - 1]) if len(ok_ms) >= 20 else None,
    }
    print(json.dumps(row))
    return row


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default=None, help="default: SiteUrl in build/outputs.json")
    ap.add_argument("--rate", type=int, default=8, help="phase 1 requests per second")
    ap.add_argument("--seconds", type=int, default=10)
    ap.add_argument("--burst", type=int, default=300)
    args = ap.parse_args()
    site = (
        args.site
        or json.loads((ROOT / "build" / "outputs.json").read_text())["AlTiempoApp"]["SiteUrl"]
    )
    url = site.rstrip("/") + "/api/health"

    # Phase 1: steady traffic under the limit.
    results, t0 = [], time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.rate * 2) as pool:
        futures = []
        for i in range(args.rate * args.seconds):
            target = t0 + i / args.rate
            time.sleep(max(0.0, target - time.perf_counter()))
            futures.append(pool.submit(hit, url))
        results = [f.result() for f in futures]
    normal = summary("normal", results, time.perf_counter() - t0)

    time.sleep(3)  # let the token bucket refill

    # Phase 2: everything at once.
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=60) as pool:
        results = list(pool.map(hit, [url] * args.burst))
    burst = summary("burst", results, time.perf_counter() - t0)

    out = ROOT / "docs" / "load-test.json"
    out.write_text(
        json.dumps(
            {"url_path": "/api/health", "limit": "10 req/s, burst 20", "results": [normal, burst]},
            indent=1,
        )
        + "\n"  # fmt: skip
    )
    print(f"Saved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
