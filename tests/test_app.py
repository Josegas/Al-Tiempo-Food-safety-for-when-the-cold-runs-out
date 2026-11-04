"""Entry point behaviour without calling Bedrock (agent replaced by a fake)."""

from types import SimpleNamespace

import pytest

import agent.app as app_mod


class FakeAgent:
    def __init__(self):
        self.messages = []
        self.state = {}
        self.state = SimpleNamespace(set=lambda k, v: None, get=lambda k: None)
        self.event_loop_metrics = SimpleNamespace(
            accumulated_usage={"inputTokens": 0, "outputTokens": 0}
        )
        self.calls = 0

    def __call__(self, prompt):
        self.calls += 1
        self.event_loop_metrics.accumulated_usage["inputTokens"] += 100
        self.event_loop_metrics.accumulated_usage["outputTokens"] += 10
        self.messages.append({"role": "assistant", "content": [{"text": "ok"}]})
        return "<thinking>internal</thinking>Eat it before 13:00."


@pytest.fixture
def fake(monkeypatch):
    agents = []

    def build(language):
        a = FakeAgent()
        agents.append(a)
        return a, SimpleNamespace(retried_count=0, blocked_count=0)

    monkeypatch.setattr(app_mod, "build_agent", build)
    app_mod._sessions.clear()
    return agents


def test_empty_prompt(fake):
    assert app_mod.invoke({"prompt": "  "}) == {"error": "empty prompt"}


def test_same_session_reuses_agent_and_counts_turn_tokens(fake):
    ctx = SimpleNamespace(session_id="s" * 40)
    r1 = app_mod.invoke({"prompt": "hola", "language": "es"}, ctx)
    r2 = app_mod.invoke({"prompt": "y ahora?", "language": "es"}, ctx)
    assert len(fake) == 1 and fake[0].calls == 2
    assert r2["metrics"]["input_tokens"] == 100  # per turn, not cumulative
    assert r1["answer"] == "Eat it before 13:00."  # thinking tags removed


def test_bad_inputs_are_sanitized(fake):
    r = app_mod.invoke({"prompt": "x" * 5000, "language": "fr", "lat": "abc", "lon": 999})
    assert r["metrics"]["language"] == "en"


def test_model_error_returns_safe_fallback(fake, monkeypatch):
    def boom(language):
        a = FakeAgent()
        a.__class__ = type("Broken", (FakeAgent,), {"__call__": lambda self, p: 1 / 0})
        return a, SimpleNamespace(retried_count=0, blocked_count=0)

    monkeypatch.setattr(app_mod, "build_agent", boom)
    r = app_mod.invoke({"prompt": "hola", "language": "es"})
    assert r["error"] == "ZeroDivisionError" and "deséchala" in r["answer"]
