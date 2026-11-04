# Costs (prices from the AWS Price List API, us-east-1, checked 2026-11-03)

## Measured
| Item | Value | How |
|---|---|---|
| Model | Amazon Nova 2 Lite (`us.amazon.nova-2-lite-v1:0`) | chosen by evals (see `docs/metrics.md`) |
| Tokens per turn | 5,669 in / 143 out (average, 36 runs) | `evals/run_evals.py` |
| **Bedrock cost per turn** | **$0.00227** | $0.00033 per 1K input, $0.00275 per 1K output |

## Estimate until judging ends (Nov 27, 2026)
Assumption: 1,000 conversation turns (judges + demo + our tests). Free tier/always-free where noted.

| Service | Price | Estimate |
|---|---|---|
| Bedrock (Nova 2 Lite) | measured $0.00227 / turn | ~$2.30 |
| AgentCore Runtime (consumption-based) | $0.0895 per vCPU-hour, $0.00945 per GB-hour (CPU billed only while active) | < $1 with a short idle timeout |
| Lambda, DynamoDB (on-demand), EventBridge Scheduler, S3, CloudFront, API Gateway | pennies at this volume; mostly free tier | < $0.50 |
| Polly (voice) | standard voices, per character | < $0.50 |
| SNS SMS | per message, depends on country; only to verified numbers in the demo | ~cents |
| AWS Budgets alerts | free | $0 |
| **Total** | | **≈ $3–5**, covered by the account's credits |

## Guardrails (implemented in `infra/`)
Budgets only **alert**; they don't stop spending. What actually limits cost:
1. API Gateway throttling: 3 requests/s, burst 10.
2. Daily conversation cap (500/day) with an atomic counter in DynamoDB; the demo answers "come back tomorrow".
3. `max_tokens=800` per model call; the verifier allows at most 1 retry.
4. AgentCore idle session timeout 5 min, max session 1 h; nothing runs 24/7 (no EC2, NAT Gateway or provisioned throughput).
5. Budget `al-tiempo-monthly` ($5, resources tagged `project=al-tiempo`): email at 50/80/100% + forecast.
6. **Kill switch:** at 100% of the budget, AWS Budgets attaches a DENY policy (Bedrock, AgentCore, Polly) to the runtime and API roles. Detach `al-tiempo-kill-switch` to resume.
7. Application inference profile so Bedrock spend for this project is visible separately in Cost Explorer.
