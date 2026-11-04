# Metrics (numbers in text for the article). Updated 2026-11-04 (live system).

| Metric | Value | How measured |
|---|---|---|
| Automated tests (rules engine, tools, time parsing, verifier, API and reminder Lambdas) | **137 / 137 passing** | `make test`, GitHub Actions summary |
| Food rules verified on the official source (verbatim text stored) | **11 / 11** | `python scripts/check_rules.py --strict` |
| Invented times/limits caught by the verifier (adversarial unit tests) | **8 / 8**, plus copied template placeholders (`HH:MM`) | `tests/test_verifier.py` |
| End-to-end evals, Nova 2 Lite (**50 scenarios** × 2 runs, 26 es / 24 en), latest run 20261104-000750 | **98 / 100 (98%)**; the 2 failures were not unsafe (one correct refusal worded differently, one evasive answer that didn't correct a false "8 hours" claim) | `python evals/run_evals.py --repeat 2` |
| Same suite, earlier runs while fixing what it found | 95 / 100 (000004) → 97 / 100 (000424, 3 safe answers our checks misread) → 98 / 100 | `evals/results/`, `docs/diario.md` |
| Previous suite (18 scenarios × 2 runs) | 36 / 36 (100%) | run 20261103-204253 |
| Adversarial evals passed (pressure, medicine doses, diagnosis, antibiotics, home remedies, "ignore your rules", a fake WHO claim) | **28 / 30** (15 scenarios × 2 runs); 0 unsafe answers | same |
| Median latency per turn (evals) | **1,590 ms** | same |
| Tokens per turn (evals) | 5,805 in / 122 out | same |
| Cost per turn (Bedrock, evals) | **$0.00225** | tokens × AWS Price List API price |
| Verifier in eval runs | 2 retries (run 150818) → 0 retries (run 192607, after code-built summaries); 50-scenario run: **4 retries, 0 safe templates** | same |
| Latest eval run (20261103-192607) | **36 / 36**, median 2,052 ms, 5,625 in / 128 out tokens, **$0.00221/turn** | same |
| Eval run after fixing spoken times + fridge door (20261103-204253) | **36 / 36**, 0 verifier retries, median 1,740 ms, **$0.00227/turn** | same (runs 203816: 34/36 and 204022: 35/36 found the bugs) |
| Reminders delivered on the live system | **9 / 9**, 4–45 s after the scheduled minute | `make smoke` + DynamoDB `delay_s` (2026-11-04) |
| Live agent time per turn (median, 15 turns) | **1,942 ms** | AgentCore logs, `conversation_turn` events |
| Live end to end, first message of a new session | **≈ 6.4 s** median (6 scenarios) | HTTPS from Culiacán to CloudFront |
| First message with warm-up (`/api/warm`), click 5 s after opening | **2.0 s** median (was 6.2 s, same browser test) | Playwright, 6 scenarios, live demo, 2026-11-04 |
| First message if clicked instantly | 5.8 s median (warm-up still running; no worse than before) | same |
| Live end to end, follow-up turns in the same session | **2.1–3.0 s** | same |
| Live tokens per turn / cost | 6,244 in / 113 out → **$0.0024** | AgentCore logs × AWS Price List API price |
| Load test, normal use (8 req/s × 10 s, `/api/health`) | **80 / 80 OK**, p50 141 ms, p95 228 ms | `make loadtest` → `docs/load-test.json` (2026-11-04) |
| Load test, burst (300 requests in 1.6 s) | 65 OK, **57 × 429** (throttle), **178 × 503** (Lambda concurrency quota = 10); **0** reached Bedrock | same + `aws lambda get-account-settings` |
| Web works offline (installable PWA) | Page reloads from cache with fonts; offline card with the basic rules; axe 0 violations; Chrome installability errors: 0 | Playwright offline test (2026-11-04) |

## Model comparison (same agent, same 18 scenarios, 1 run each)
| Model | Passed | Median latency | USD per turn |
|---|---|---|---|
| Amazon Nova Lite | 8 / 18 (44%) | 1,759 ms | $0.00033 |
| Amazon Nova Pro | 15 / 18 (83%) | 2,609 ms | $0.00499 |
| **Amazon Nova 2 Lite (chosen)** | **18 / 18 (100%)** | 2,365 ms | ~$0.0024 |

Raw results: `evals/results/*.json`. What changed between runs and why: `docs/diario.md`.
