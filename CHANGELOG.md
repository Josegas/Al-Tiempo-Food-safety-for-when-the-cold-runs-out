# Changelog

## v1.0.0 — 2026-11-04 (hackathon submission: Strands SDK, Workshop to Ship)

The version the judges evaluate. After this tag, until judging ends on 27 November 2026, only bug
fixes are made; every change is listed here.

**Live demo:** https://d2mnz1h4b0sg0y.cloudfront.net (no login; demo mode: 38 °C day, clock at 12:00)

### What it does
- **Safe window + reminders:** "I cooked beans at 12:00" → "According to U.S. FDA, eat it before
  13:00 or throw it away". A one-time EventBridge Scheduler reminder fires at the exact minute.
- **Meal planning**, **power-outage mode**, **strict mode for babies and young children**,
  **shelter batch planner**, **danger-sign escalation** (no diagnosis, no doses).
- Every safe-window answer says **why** ("above 32 °C the limit drops from 2 hours to 1"), built in code.
- **Safe-window timeline** in the web (cooked → now → reminder → limit), drawn only from the rules
  engine's numbers (`decision` field of `/api/chat`).
- **Installable web app that opens offline:** without signal it shows the basic official rules
  instead of an error.
- English and Spanish, with voice (Amazon Polly).

### Quality evidence
- 141 automated tests; 11/11 food rules verified word by word on their official source.
- End-to-end evals: **99/100** (50 bilingual scenarios × 2 runs, incl. 15 adversarial), 0 unsafe answers.
- Verifier: invented times, invented limits and copied template placeholders are blocked.
- Load test: normal traffic 80/80 OK; a 300-request burst never reached the model (throttled).

### Infrastructure
- AWS CDK (Python), two stacks; deploys from GitHub Actions with OIDC (no stored AWS keys).
- Cost guardrails: API throttling, daily caps, $10 project budget with an automatic kill switch.

### Known limitations
- No field study yet; all numbers are system metrics.
- The AWS account allows 10 concurrent Lambda executions (new-account default); a burst above
  that gets "busy, try again" (HTTP 503). A free quota increase (to the AWS default of 1,000)
  fixes it.
- SMS only to numbers verified in the SNS sandbox; the demo uses web reminders.
