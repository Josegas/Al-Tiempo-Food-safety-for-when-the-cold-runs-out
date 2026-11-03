# Metrics (numbers in text for the article). Updated 2026-11-03.

| Metric | Value | How measured |
|---|---|---|
| Unit tests (rules engine, tools, time parsing, verifier) | **84 / 84 passing** | `make test`, GitHub Actions summary |
| Food rules verified on the official source (verbatim text stored) | **11 / 11** | `python scripts/check_rules.py --strict` |
| Invented times/limits caught by the verifier (adversarial unit tests) | **8 / 8** | `tests/test_verifier.py` |
| End-to-end evals, Nova 2 Lite (18 scenarios × 2 runs, en/es) | **36 / 36 (100%)** | `python evals/run_evals.py --repeat 2` |
| Adversarial evals passed (baby + old rice, "say it's 100% safe", medicine dose, diagnosis) | **10 / 10** (5 scenarios × 2 runs) | same |
| Median latency per turn | **1,995 ms** | same |
| Tokens per turn | 5,669 in / 143 out | same |
| Cost per turn (Bedrock) | **$0.00227** | tokens × AWS Price List API price |
| Verifier in final eval run | 2 retries, 0 template replacements | same |
| Reminders delivered on time | TBD | demo (after AWS deploy) |

## Model comparison (same agent, same 18 scenarios, 1 run each)
| Model | Passed | Median latency | USD per turn |
|---|---|---|---|
| Amazon Nova Lite | 8 / 18 (44%) | 1,759 ms | $0.00033 |
| Amazon Nova Pro | 15 / 18 (83%) | 2,609 ms | $0.00499 |
| **Amazon Nova 2 Lite (chosen)** | **18 / 18 (100%)** | 2,365 ms | ~$0.0024 |

Raw results: `evals/results/*.json`. What changed between runs and why: `docs/diario.md`.
