# Al Tiempo — food safety for when the cold runs out

[![CI](https://github.com/Josegas/Al-Tiempo-Food-safety-for-when-the-cold-runs-out/actions/workflows/ci.yml/badge.svg)](https://github.com/Josegas/Al-Tiempo-Food-safety-for-when-the-cold-runs-out/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

An AI agent built with the **Strands Agents SDK** on **AWS** that tells families without reliable
refrigeration — and shelters / community kitchens after disasters — **until what time cooked food
is safe to eat today**, based on official food-safety rules and the hourly heat forecast.

> **Design principle:** the model talks and explains; official rules decide; when in doubt, the safest option.
> The LLM never computes times or limits: a deterministic, tested rules engine does, and a verifier hook
> blocks any answer whose times don't match the engine.

## Try it in 1 minute
_Live demo link: coming soon (AWS deployment in progress)._

Locally (Python 3.11+, AWS credentials with Bedrock access):
```bash
git clone https://github.com/Josegas/Al-Tiempo-Food-safety-for-when-the-cold-runs-out.git
cd Al-Tiempo-Food-safety-for-when-the-cold-runs-out
make install          # venv + dependencies
cp .env.example .env  # DEMO_MODE=true uses a saved 38 °C forecast
make check            # lint + rules policy + tests
make chat             # chat in Spanish (make chat CHAT_LANG=en for English)
```

## What it does
1. **Safe window + reminders** — "I cooked beans at 12:00" → "According to the U.S. FDA, eat them before 13:00 or throw them away" (38 °C day → 1-hour rule).
2. **Meal planning** — when to cook and how much, so nothing sits out.
3. **Power-outage mode** — fridge/freezer clock from the moment the power went out.
4. **Strict mode for babies and young children.**
5. **Shelters & community kitchens** — staggered cooking batches with discard times.
6. **Danger-sign escalation** — fixed WHO dehydration questions → "go to a clinic / call 911". No diagnosis, no doses.

## How it works
| Piece | Where |
|---|---|
| Rules as data (each with official source) | `rules/food_rules.yaml`, `rules/danger_signs.yaml` |
| Deterministic rules engine (pure Python, tested) | `agent/rules_engine.py` |
| Strands tools (one per file) | `agent/tools/` |
| Verifier hook (`AfterToolCallEvent` + `AfterModelCallEvent`, retry → safe template) | `agent/hooks/verifier.py` |
| AgentCore Runtime entrypoint (structured logs: latency, tokens, verifier blocks) | `agent/app.py` |
| Forecast: Open-Meteo, or fixtures in demo mode | `agent/forecast.py`, `fixtures/` |

## Engineering practices
- **CI (GitHub Actions):** ruff lint/format, pytest + coverage summary, rules policy check.
- **Security:** gitleaks secret scan, pip-audit dependency scan, bandit-style static rules, Dependabot.
- **Policy as code:** a release (`v*` tag) is blocked while any food rule is not verified on its official source.
- **Safety regression tests:** every real unsafe answer we found becomes a test (see `docs/diario.md`).
- **Evals drive decisions:** 18 bilingual scenarios (incl. adversarial ones) picked the model —
  Nova Lite 8/18, Nova Pro 15/18, **Nova 2 Lite 18/18** — and now pass 36/36 at $0.00227 per turn
  (`docs/metrics.md`, `docs/costs.md`). Every number we publish is in `docs/sources.md`.

## Rule sources (all verified on 2026-11-03)
Every rule in `rules/food_rules.yaml` stores the **verbatim sentence** from its official page
(`verified_text`) so anyone can check it with Ctrl+F. Sources: WHO *Five keys to safer food*,
U.S. FDA, CDC (infant formula), NHS (cooked rice). One rule is marked `adapted` (rice without a
fridge) and one is a `policy` (stricter mode for young children); both say so to the user.
CI blocks a release if any rule is unverified (`python scripts/check_rules.py --strict`).

## Disclaimer
Al Tiempo gives general food-safety guidance from public health sources. It is not medical advice.
In an emergency, call your local emergency number.

## License
[MIT](LICENSE)
