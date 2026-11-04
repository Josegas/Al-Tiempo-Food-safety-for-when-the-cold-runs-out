"""End-to-end evals against Bedrock. Deterministic pass/fail checks per scenario.

  python evals/run_evals.py                          # model from MODEL_ID
  python evals/run_evals.py --models a,b --repeat 2  # compare models

Writes evals/results/<timestamp>.json and prints a markdown summary (copy it to docs/metrics.md).
Runs in DEMO_MODE (38 °C fixture, clock fixed at 12:00) so expected answers are stable.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("ALLOW_UNVERIFIED_RULES", "true")

from agent.agent import build_agent, clean_answer  # noqa: E402

# USD per 1K tokens, us-east-1 on-demand, from the AWS Price List API (2026-11-03).
PRICES = {
    "us.amazon.nova-micro-v1:0": (0.000035, 0.00014),
    "us.amazon.nova-lite-v1:0": (0.00006, 0.00024),
    "us.amazon.nova-pro-v1:0": (0.0008, 0.0032),
    "us.amazon.nova-2-lite-v1:0": (0.00033, 0.00275),
}


def tools_called(messages: list) -> list[str]:
    return [b["toolUse"]["name"] for m in messages for b in m["content"] if "toolUse" in b]


def check(s: dict, answer: str, tools: list[str]) -> list[str]:
    fails = []
    low = answer.lower()
    if s.get("expect_tool") and s["expect_tool"] not in tools:
        fails.append(f"tool {s['expect_tool']} not called (got {tools})")
    if s.get("must_contain_any") and not any(x.lower() in low for x in s["must_contain_any"]):
        fails.append(f"missing any of {s['must_contain_any']}")
    for bad in s.get("must_not_contain", []):
        if bad.lower() in low:
            fails.append(f"contains forbidden '{bad}'")
    if "hh:mm" in low or "<rule" in low or "<regla" in low:
        fails.append("contains a template placeholder")
    return fails


def run(model: str, scenarios: list[dict], repeat: int) -> dict:
    os.environ["MODEL_ID"] = model
    rows = []
    for _ in range(repeat):
        for s in scenarios:
            agent, verifier = build_agent(s["lang"])
            t0 = time.perf_counter()
            try:
                answer = clean_answer(str(agent(s["prompt"])))
                error = None
            except Exception as exc:
                answer, error = "", type(exc).__name__
            ms = int((time.perf_counter() - t0) * 1000)
            usage = agent.event_loop_metrics.accumulated_usage
            tools = tools_called(agent.messages)
            fails = [f"error {error}"] if error else check(s, answer, tools)
            rows.append({
                "id": s["id"], "category": s["category"], "passed": not fails, "fails": fails,
                "answer": answer, "tools": tools, "latency_ms": ms,
                "input_tokens": usage["inputTokens"], "output_tokens": usage["outputTokens"],
                "verifier_retried": verifier.retried_count, "verifier_blocked": verifier.blocked_count,
                "verifier_violations": verifier.violations,
            })  # fmt: skip
            mark = "PASS" if not fails else "FAIL"
            print(f"  [{mark}] {s['id']:<26} {ms:>6} ms {fails if fails else ''}", flush=True)
    pin, pout = PRICES.get(model, (None, None))
    tin = sum(r["input_tokens"] for r in rows)
    tout = sum(r["output_tokens"] for r in rows)
    cost = (tin / 1000 * pin + tout / 1000 * pout) if pin is not None else None
    return {
        "model": model,
        "runs": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "median_latency_ms": int(statistics.median(r["latency_ms"] for r in rows)),
        "avg_input_tokens": int(tin / len(rows)),
        "avg_output_tokens": int(tout / len(rows)),
        "cost_per_turn_usd": round(cost / len(rows), 6) if cost is not None else None,
        "verifier_retries": sum(r["verifier_retried"] for r in rows),
        "verifier_blocks": sum(r["verifier_blocked"] for r in rows),
        "rows": rows,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=os.getenv("MODEL_ID", "us.amazon.nova-2-lite-v1:0"))
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default=None, help="comma-separated scenario ids")
    args = ap.parse_args()
    scenarios = json.loads((ROOT / "evals" / "scenarios.json").read_text(encoding="utf-8"))
    if args.only:
        scenarios = [s for s in scenarios if s["id"] in args.only.split(",")]
    results = []
    for model in args.models.split(","):
        print(f"\n== {model}")
        results.append(run(model.strip(), scenarios, args.repeat))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = ROOT / "evals" / "results" / f"{stamp}.json"
    out.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    print(
        "\n| Model | Passed | Median latency | Tokens in/out per turn | USD per turn | Verifier retries / blocks |"
    )
    print("|---|---|---|---|---|---|")
    for r in results:
        pct = 100 * r["passed"] / r["runs"]
        cost = f"${r['cost_per_turn_usd']:.5f}" if r["cost_per_turn_usd"] is not None else "n/a"
        print(f"| {r['model']} | {r['passed']}/{r['runs']} ({pct:.0f}%) | {r['median_latency_ms']} ms | "
              f"{r['avg_input_tokens']}/{r['avg_output_tokens']} | {cost} | "
              f"{r['verifier_retries']} / {r['verifier_blocks']} |")  # fmt: skip
    print(f"\nSaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
