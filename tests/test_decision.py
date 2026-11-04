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


# ---------------- shelter plan (batch timeline) ----------------
from agent.decision import shelter_plan_decision  # noqa: E402
from agent.rules_engine import plan_shelter_batches  # noqa: E402

HOT_DAY = [(datetime(2026, 11, 3, h), 38.0) for h in range(24)]


def _plan(hot_hold=False):
    w = [(datetime(2026, 11, 3, 13, 0), datetime(2026, 11, 3, 15, 0))]
    return plan_shelter_batches(120, w, ["rice", "beans"], hot_hold, HOT_DAY)


def test_shelter_decision_copies_every_batch_time_from_the_engine():
    plan = _plan()
    d = shelter_plan_decision(_turn(plan, name="plan_shelter_batches"))
    assert d["kind"] == "shelter_plan" and d["people"] == 120 and d["hot_hold"] is False
    assert [b["ready_hhmm"] for b in d["batches"]] == [b["ready_hhmm"] for b in plan["batches"]]
    assert [b["discard_hhmm"] for b in d["batches"]] == ["14:00", "15:00"]
    assert [b["start_cooking_hhmm"] for b in d["batches"]] == ["12:00", "13:00"]
    assert d["batches"][0]["portions"] == 60
    assert d["source"] == {"kind": "official", "name": "U.S. FDA"}
    assert "sources" not in d and "assumptions" not in d


def test_shelter_decision_hot_holding():
    d = shelter_plan_decision(_turn(_plan(hot_hold=True), name="plan_shelter_batches"))
    assert d["hot_hold"] is True and d["batches"][0]["keep_above_c"] == 60
    assert d["source"]["name"] == "WHO"


def test_no_shelter_decision_for_other_tools_or_errors():
    assert shelter_plan_decision(_turn(_plan(), name="plan_meals")) is None
    assert shelter_plan_decision(_turn({"error": "No valid service windows"}, name="plan_shelter_batches")) is None  # fmt: skip
    assert (
        shelter_plan_decision(_turn(_plan(), name="plan_shelter_batches", status="error")) is None
    )


def test_safe_window_wins_over_shelter_in_the_same_turn():
    turn = _turn(_engine_result()) + _turn(_plan(), name="plan_shelter_batches")
    assert safe_window_decision(turn)["kind"] == "safe_window"


# ---------------- comprehension check (one-tap question after a safe window) ----------------
from agent.rules_engine import comprehension_options  # noqa: E402


def test_quiz_options_are_deterministic_and_include_the_engine_time():
    eat_by, now = datetime(2026, 11, 3, 13, 0), datetime(2026, 11, 3, 12, 0)
    q = comprehension_options(eat_by, now)
    assert q == {"options": ["12:30", "13:00", "14:00"], "correct": "13:00"}
    assert comprehension_options(eat_by, now) == q  # same input, same options
    # 30 min earlier would already be past: the second distractor is 2 h later instead
    q2 = comprehension_options(datetime(2026, 11, 3, 12, 15), now)
    assert q2 == {"options": ["12:15", "13:15", "14:15"], "correct": "12:15"}


def test_decision_carries_quiz_only_when_there_is_time_left():
    d = safe_window_decision(_turn(_engine_result(now_h=12, cooked_h=12)))
    assert d["quiz"]["correct"] == d["eat_by_hhmm"] == "13:00"
    assert d["quiz"]["options"] == ["12:30", "13:00", "14:00"]
    assert (
        safe_window_decision(_turn(_engine_result(now_h=12, cooked_h=10)))["quiz"] is None
    )  # expired
    r = _engine_result(now_h=12, cooked_h=12)
    r["time_source"] = "unknown"
    assert safe_window_decision(_turn(r))["quiz"] is None


def test_quiz_never_reaches_the_model():
    # The distractors live only in the API response, not in the tool result the model and the
    # verifier see, so the verifier can't be tricked into allowing "14:00".
    r = _engine_result(now_h=12, cooked_h=12)
    assert "quiz" not in r and "14:00" not in json.dumps(r)
