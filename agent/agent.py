"""Creates the Al Tiempo Strands agent."""

from __future__ import annotations

import os
from pathlib import Path

from strands import Agent
from strands.models import BedrockModel

from agent.hooks.verifier import VerifierHook
from agent.tools import ALL_TOOLS

PROMPTS = Path(__file__).resolve().parent / "prompts"
DEFAULT_MODEL = "us.amazon.nova-lite-v1:0"


def system_prompt(language: str) -> str:
    lang = language if language in ("en", "es") else "en"
    return (PROMPTS / f"system_{lang}.md").read_text(encoding="utf-8")


def build_agent(language: str = "en", messages: list | None = None) -> tuple[Agent, VerifierHook]:
    verifier = VerifierHook(language=language)
    model = BedrockModel(
        model_id=os.getenv("MODEL_ID", DEFAULT_MODEL),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        temperature=0.2,
        max_tokens=800,
    )
    agent = Agent(
        model=model,
        system_prompt=system_prompt(language),
        tools=ALL_TOOLS,
        hooks=[verifier],
        messages=messages,
        callback_handler=None,
    )
    return agent, verifier


if __name__ == "__main__":  # local chat: python -m agent.agent es
    import sys

    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    agent, verifier = build_agent(lang)
    print("Al Tiempo (Ctrl+C to exit)")
    while True:
        try:
            text = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        print(agent(text))
        print(f"[verifier] retried={verifier.retried_count} blocked={verifier.blocked_count}")
