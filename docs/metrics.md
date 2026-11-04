# Metrics (numbers in text for the article). Updated 2026-11-04 (live system).

| Metric | Value | How measured |
|---|---|---|
| Automated tests (rules engine, tools, time parsing, verifier, API and reminder Lambdas) | **107 / 107 passing** | `make test`, GitHub Actions summary |
| Food rules verified on the official source (verbatim text stored) | **11 / 11** | `python scripts/check_rules.py --strict` |
| Invented times/limits caught by the verifier (adversarial unit tests) | **8 / 8** | `tests/test_verifier.py` |
| End-to-end evals, Nova 2 Lite (18 scenarios × 2 runs, en/es) | **36 / 36 (100%)** | `python evals/run_evals.py --repeat 2` |
| Adversarial evals passed (baby + old rice, "say it's 100% safe", medicine dose, diagnosis) | **10 / 10** (5 scenarios × 2 runs) | same |
| Median latency per turn | **1,995 ms** | same |
| Tokens per turn | 5,669 in / 143 out | same |
| Cost per turn (Bedrock) | **$0.00227** | tokens × AWS Price List API price |
| Verifier in final eval run | 2 retries, 0 template replacements | same |
| Reminders delivered on the live system | **4 / 4**, 7–42 s after the scheduled minute | `make smoke` + DynamoDB `delay_s` (2026-11-04) |
| Live agent time per turn (median, 15 turns) | **1,942 ms** | AgentCore logs, `conversation_turn` events |
| Live end to end, first message of a new session | **≈ 6.4 s** median (6 scenarios) | HTTPS from Culiacán to CloudFront |
| Live end to end, follow-up turns in the same session | **2.1–3.0 s** | same |
| Live tokens per turn / cost | 6,244 in / 113 out → **$0.0024** | AgentCore logs × AWS Price List API price |

## Model comparison (same agent, same 18 scenarios, 1 run each)
| Model | Passed | Median latency | USD per turn |
|---|---|---|---|
| Amazon Nova Lite | 8 / 18 (44%) | 1,759 ms | $0.00033 |
| Amazon Nova Pro | 15 / 18 (83%) | 2,609 ms | $0.00499 |
| **Amazon Nova 2 Lite (chosen)** | **18 / 18 (100%)** | 2,365 ms | ~$0.0024 |

Raw results: `evals/results/*.json`. What changed between runs and why: `docs/diario.md`.
