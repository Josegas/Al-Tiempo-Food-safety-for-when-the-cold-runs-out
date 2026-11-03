# Metrics (filled in from CI and evals — numbers in text for the article)

| Metric | Value | How measured |
|---|---|---|
| Rules engine + tool tests passing | 58 / 58 (2026-11-03) | `make test`, GitHub Actions summary |
| Rules verified on official source | 1 / 11 (pending manual verification) | `python scripts/check_rules.py` |
| Invented times/limits blocked by verifier (unit) | 8 / 8 | `tests/test_verifier.py` |
| Agent answers consistent with engine | TBD (X / Y scenarios) | `evals/run_evals.py` |
| Unsafe answers blocked (adversarial) | TBD | evals |
| Reminders delivered on time | TBD | demo |
| Median latency | ~2.7 s (smoke test, Nova Lite, 6 prompts) | structured logs |
| Tokens per turn | ~5k in / ~250 out (smoke test) | structured logs |
| Cost per conversation (USD) | TBD | tokens x Bedrock price |
