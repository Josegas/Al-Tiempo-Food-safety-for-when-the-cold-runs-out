"""Creates the Al Tiempo Strands agent."""

from __future__ import annotations

import os
import re
from pathlib import Path

from strands import Agent
from strands.models import BedrockModel

from agent.hooks.objections import ObjectionHook
from agent.hooks.verifier import VerifierHook
from agent.tools import ALL_TOOLS

PROMPTS = Path(__file__).resolve().parent / "prompts"
THINKING_RE = re.compile(r"<thinking>.*?</thinking>", re.DOTALL)


def clean_answer(text: str) -> str:
    """Removes model 'thinking' tags that some models (e.g. Nova) leak into the answer."""
    return THINKING_RE.sub("", text).strip()


DEFAULT_MODEL = "us.amazon.nova-2-lite-v1:0"


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
        hooks=[
            ObjectionHook(language=language),
            verifier,
        ],  # objections first: verifier sees the note
        messages=messages,
        callback_handler=None,
    )
    # Tools build their summaries in this language. app.py sets it too; setting it here makes
    # local chat and evals behave like production (eval bug: Spanish user got an English summary).
    agent.state.set("language", language if language in ("en", "es") else "en")
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
        print(clean_answer(str(agent(text))))
        print(f"[verifier] retried={verifier.retried_count} blocked={verifier.blocked_count}")
