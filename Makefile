.PHONY: figures install lint format test rules check chat evals package synth diff-access deploy-access dev-profile diff deploy smoke outputs activate-cost-tag

CHAT_LANG ?= es
ADMIN_PROFILE ?= default
DEV_PROFILE ?= al-tiempo
CDK = cd infra && JSII_RUNTIME_PACKAGE_CACHE=disabled CDK_DISABLE_CLI_TELEMETRY=true PATH="$(CURDIR)/.venv/bin:$$PATH" npx -y aws-cdk@2.1147.0
ENV_FILE = set -a; [ -f .env ] && . ./.env; set +a;

install:
	python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt -r infra/requirements.txt

lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

format:
	.venv/bin/ruff check --fix . && .venv/bin/ruff format .

test:
	.venv/bin/python -m pytest --cov=agent --cov-report=term-missing

rules:
	.venv/bin/python scripts/check_rules.py --strict

check: lint rules test

chat:  ## local chat against Bedrock; usage: make chat CHAT_LANG=en
	$(ENV_FILE) .venv/bin/python -m agent.agent $(CHAT_LANG)

evals:  ## end-to-end evals against Bedrock (costs cents)
	$(ENV_FILE) .venv/bin/python evals/run_evals.py --repeat 2

# ---------------- AWS (see docs/devops.md) ----------------
package:  ## build/agent.zip (ARM64) + boto3 layer, no Docker
	.venv/bin/python scripts/package_agent.py

synth: package
	$(CDK) synth --quiet

diff-access:  ## admin, once: review IAM user/group, GitHub OIDC role, budget, alarms
	$(ENV_FILE) $(CDK) diff AlTiempoAccess --profile $(ADMIN_PROFILE)

deploy-access:  ## admin, once (asks you to approve IAM changes)
	$(ENV_FILE) $(CDK) deploy AlTiempoAccess --profile $(ADMIN_PROFILE)

dev-profile:  ## admin, once: access key for al-tiempo-dev -> AWS CLI profile "al-tiempo"
	ADMIN_PROFILE=$(ADMIN_PROFILE) ./scripts/setup_dev_profile.sh

diff: package
	$(CDK) diff AlTiempoApp --profile $(DEV_PROFILE)

deploy: package  ## day to day, with the least-privilege dev user
	$(CDK) deploy AlTiempoApp --profile $(DEV_PROFILE) --outputs-file ../build/outputs.json

outputs:
	@.venv/bin/python -c "import json;o=json.load(open('build/outputs.json'))['AlTiempoApp'];[print(f'{k}: {v}') for k,v in o.items()]"

smoke:  ## end-to-end check of the deployed demo
	.venv/bin/python scripts/smoke_test.py

activate-cost-tag:  ## admin: make the "project" tag usable in budgets/Cost Explorer (can take 24 h)
	aws ce update-cost-allocation-tags-status --cost-allocation-tags-status TagKey=project,Status=Active --profile $(ADMIN_PROFILE)

figures:  ## article images from code + eval results (needs Pillow)
	python3 scripts/make_figures.py
