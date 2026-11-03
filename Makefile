.PHONY: install lint format test rules check chat

CHAT_LANG ?= es

install:
	python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

lint:
	.venv/bin/ruff check . && .venv/bin/ruff format --check .

format:
	.venv/bin/ruff check --fix . && .venv/bin/ruff format .

test:
	.venv/bin/python -m pytest --cov=agent --cov-report=term-missing

rules:
	.venv/bin/python scripts/check_rules.py

check: lint rules test

chat:  ## local chat against Bedrock (needs AWS credentials); usage: make chat CHAT_LANG=en
	set -a; [ -f .env ] && . ./.env; set +a; .venv/bin/python -m agent.agent $(CHAT_LANG)
