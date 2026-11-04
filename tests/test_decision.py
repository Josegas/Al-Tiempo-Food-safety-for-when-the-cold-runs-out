"""The `decision` field the web uses to draw the safe-window timeline."""

import io
import json
from datetime import datetime
from types import SimpleNamespace

from agent.decision import safe_window_decision
from agent.rules_engine import compute_safe_window
from tests.test_lambdas import SESSION, event


def _turn(result: dict, name="compute_safe_window", status="success"):
    return [
        {"role": "assistant", "content": [{"toolUse": {"toolUseId": "t1", "name": name, "input": {}}}]},
        {"role": "user", "content": [{"toolResult": {"toolUseId": "t1", "status": status,
                                                     "content": [{"text": json.dumps(result)}]}}]},
        {"role": "assistant", "content": [{"text": "Eat it before 13:00."}]},
    ]  # fmt: skip


def _engine_result(now_h=12, cooked_h=10):
    now = datetime(2026, 11, 3, now_h, 0)
    r = compute_safe_window("cooked_food", datetime(2026, 11, 3, cooked_h, 0), "general", [(datetime(2026, 11, 3, h), 38.0) for h in range(24)], None, now=now).to_dict()  # fmt: skip
    r.update(
        cooked_at_hhmm=f"{cooked_h:02d}:00", now_hhmm=f"{now_h:02d}:00", time_source="user_text"
    )
    return r


def test_decision_copies_engine_numbers_only():
    r = _engine_result()
    d = safe_window_decision(_turn(r))
    assert d["kind"] == "safe_window"
    assert d["eat_by_hhmm"] == r["eat_by_hhmm"]
    assert d["reminder_at_hhmm"] == r["reminder_at"][11:16]
    assert d["cooked_at_hhmm"] == "10:00" and d["now_hhmm"] == "12:00"
    assert d["status"] == r["status"] and d["cooked_known"] is True
    assert d["source"]["kind"] == "official" and " - " not in (d["source"]["name"] or "")
    assert "sources" not in d and "assumptions" not in d  # nothing the web doesn't need


def test_no_decision_without_safe_window():
    assert safe_window_decision([{"role": "assistant", "content": [{"text": "hola"}]}]) is None
    assert safe_window_decision(_turn(_engine_result(), name="track_outage")) is None
    assert safe_window_decision(_turn(_engine_result(), status="error")) is None


def test_unknown_cooking_time_is_flagged():
    r = _engine_result()
    r["time_source"] = "unknown"
    assert safe_window_decision(_turn(r))["cooked_known"] is False


def test_api_passes_decision_through(monkeypatch):
    from tests.test_lambdas import load

    api = load("api", monkeypatch)
    from tests.test_lambdas import FakeTable

    api.TABLE = FakeTable()
    decision = {"kind": "safe_window", "eat_by_hhmm": "13:00"}

    def invoke(**kw):
        body = {"answer": "ok", "metrics": {}, "decision": decision}
        return {"response": io.BytesIO(json.dumps(body).encode())}

    api.AGENTCORE = SimpleNamespace(invoke_agent_runtime=invoke)
    r = api.handler(event("POST /api/chat", {"prompt": "hola", "session_id": SESSION}), None)
    assert json.loads(r["body"])["decision"] == decision


def test_decision_carries_the_reason_data():
    d = safe_window_decision(_turn(_engine_result()))
    assert d["rule_id"] == "FDA_HOT_1H" and d["max_temp_c"] == 38.0 and d["hot_threshold_c"] == 32.0


def test_summary_explains_why_from_engine_data():
    """User feedback: the answer said what to do but not why. The reason is built in code."""
    from agent.tools.safe_window_tool import window_reason, window_summary

    r = _engine_result()
    es = window_summary(r, "es")
    assert "Con más de 32 °C (el pronóstico llega a 38 °C), el límite baja de 2 horas a 1." in es
    mild = {"deciding_source": {"rule_id": "FDA_2H"}, "max_temp_c": 28.5, "hot_threshold_c": 32.0}
    assert "máximo 28.5 °C" in window_reason(mild, "es") and "2 hours" in window_reason(mild, "en")
    no_forecast = {**mild, "deciding_source": {"rule_id": "FDA_HOT_1H"}, "max_temp_c": None}
    assert "Without a weather forecast" in window_reason(no_forecast, "en")
    assert window_reason({"deciding_source": {"rule_id": "CDC_FORMULA_2H"}}, "es") == ""


def test_reason_passes_the_verifier():
    from agent.hooks.verifier import collect_allowed, find_unbacked
    from agent.tools.safe_window_tool import window_summary

    r = _engine_result()
    text = window_summary(r, "en")
    assert find_unbacked(text, *collect_allowed(json.dumps(r))) == {"times": [], "minutes": []}
