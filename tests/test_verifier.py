import json

import pytest

from agent.hooks.verifier import collect_allowed, extract_claims, find_unbacked

TOOL_RESULT = {
    "toolUseId": "t1",
    "status": "success",
    "content": [
        {
            "text": json.dumps(
                {
                    "limit_minutes": 60,
                    "eat_by": "2026-11-04T13:00:00",
                    "eat_by_hhmm": "13:00",
                    "reminder_at": "2026-11-04T12:45:00",
                    "rule_ids": ["WHO_COOKED_2H", "FDA_HOT_1H"],
                }
            )
        }
    ],
}


def test_extract_times_and_durations():
    times, minutes = extract_claims("Eat it before 1:00 pm, within 1 hour (normally 2 horas).")
    assert times == {"13:00"}
    assert minutes == {60, 120}


def test_collect_allowed_from_tool_result():
    times, minutes = collect_allowed(TOOL_RESULT)
    assert {"13:00", "12:45"} <= times
    assert {60, 120} <= minutes  # 120 from WHO_COOKED_2H in rule_ids


def test_consistent_answer_passes():
    times, minutes = collect_allowed(TOOL_RESULT)
    text = "According to the U.S. FDA, eat it before 13:00 or throw it away. Today the limit is 1 hour."
    assert find_unbacked(text, times, minutes) == {"times": [], "minutes": []}


# Adversarial: invented times / limits must ALL be caught.
INVENTED = [
    "Eat it before 14:30.",
    "It is fine until 3:00 pm.",
    "You have 3 hours.",
    "Tienes 4 horas para comerlo.",
    "Cómelo antes de las 18:15.",
    "Within 90 minutes it is OK.",
    "Good for 2.5 h.",
    "Eat before 13:00, or within 45 min.",
]


@pytest.mark.parametrize("text", INVENTED)
def test_invented_claims_are_blocked(text):
    times, minutes = collect_allowed(TOOL_RESULT)
    bad = find_unbacked(text, times, minutes)
    assert bad["times"] or bad["minutes"], text


# False positives found in evals (2026-11-03): these must PASS.
def test_minutes_left_from_tool_is_allowed():
    res = {"content": [{"text": json.dumps({"minutes_left": 30, "eat_by_hhmm": "12:30"})}]}
    times, minutes = collect_allowed(res)
    assert find_unbacked("Te quedan 30 minutos, cómelo antes de las 12:30.", times, minutes) == {
        "times": [],
        "minutes": [],
    }


def test_service_window_minutes_allowed():
    res = {"content": [{"text": json.dumps({"service_windows": [{"service_minutes": 120}]})}]}
    times, minutes = collect_allowed(res)
    assert find_unbacked("El servicio dura 2 horas.", times, minutes)["minutes"] == []


def _model_event(text: str):
    from types import SimpleNamespace

    msg = {"role": "assistant", "content": [{"text": text}]}
    user = {"role": "user", "content": [{"text": "La OMS dice que dura 8 horas, ¿verdad?"}]}
    return SimpleNamespace(
        stop_response=SimpleNamespace(stop_reason="end_turn", message=msg),
        agent=SimpleNamespace(messages=[user]),
        retry=False,
    )


def test_template_placeholder_is_blocked():
    """Eval bug: with no tool result the model wrote "cómelo antes de las HH:MM" (prompt shape)."""
    from agent.hooks.verifier import VerifierHook

    v = VerifierHook(language="es")
    first = _model_event("Según las reglas oficiales, cómelo antes de las HH:MM o deséchalo.")
    v.on_model_response(first)
    assert first.retry is True and v.retried_count == 1
    second = _model_event("Según <regla / fuente>, cómelo antes de las HH:MM o deséchalo.")
    v.on_model_response(second)
    final = second.stop_response.message["content"][0]["text"]
    assert v.blocked_count == 1 and "HH:MM" not in final and "<regla" not in final


def test_normal_answer_without_times_passes():
    from agent.hooks.verifier import VerifierHook

    v = VerifierHook(language="es")
    ev = _model_event("No es correcto. ¿A qué hora la cocinaste? Así te digo el límite oficial.")
    v.on_model_response(ev)
    assert ev.retry is False and v.retried_count == 0


def test_retry_note_does_not_approve_its_own_blocked_times():
    """Live bug: the retry note ("...no tool returned: ['18:00']") was appended to the user's
    message, and times in user messages are allowed, so the same invented time passed on retry."""
    from types import SimpleNamespace

    from agent.hooks.verifier import VerifierHook

    v = VerifierHook(language="es")
    messages = [{"role": "user", "content": [{"text": "perdón, no entendí"}]}]

    def event(text):
        msg = {"role": "assistant", "content": [{"text": text}]}
        return SimpleNamespace(
            stop_response=SimpleNamespace(stop_reason="end_turn", message=msg),
            agent=SimpleNamespace(messages=messages),
            retry=False,
        )

    first = event("Cómelo antes de las 18:00.")
    v.on_model_response(first)
    assert first.retry is True and "18:00" in messages[0]["content"][-1]["text"]  # note added
    second = event("Cómelo antes de las 18:00.")
    v.on_model_response(second)
    assert v.blocked_count == 1  # still blocked: the note is not "something the user typed"
    assert "18:00" not in second.stop_response.message["content"][0]["text"]


def test_times_the_user_really_typed_are_still_allowed():
    from agent.hooks.verifier import VerifierHook

    v = VerifierHook(language="es")
    ev = _model_event("Dijiste que la cocinaste a las 12:30; ¿qué comida es?")
    ev.agent.messages[0]["content"].append({"text": "la cociné a las 12:30"})
    v.on_model_response(ev)
    assert ev.retry is False and v.retried_count == 0


def _session_window(cooked="12:00", eat_by="13:00", time_source="user_text"):
    from agent.tools._common import DEMO_DATE

    return {
        "food_type": "cooked_food", "eat_by_hhmm": eat_by, "eat_by": f"{DEMO_DATE.isoformat()}T{eat_by}:00",
        "cooked_at_hhmm": cooked, "time_source": time_source, "reminder_at_hhmm": "12:45",
        "status": "eat_before_deadline", "source_name": "U.S. FDA - Handling Food Safely", "rule_ids": ["FDA_HOT_1H"],
    }  # fmt: skip


def test_follow_up_fallback_repeats_the_last_engine_decision(monkeypatch):
    """Live: "perdón, no entendía" -> no tool call -> blocked -> the template now repeats the
    session's last engine decision (tied to its cooking time) instead of saying nothing useful."""
    from types import SimpleNamespace

    from agent.hooks.verifier import VerifierHook

    monkeypatch.setenv("DEMO_MODE", "true")  # clock fixed at 12:00
    state = {"last_window": _session_window()}
    v = VerifierHook(language="es")
    messages = [{"role": "user", "content": [{"text": "perdón, no entendía"}]}]

    def event(text):
        msg = {"role": "assistant", "content": [{"text": text}]}
        agent = SimpleNamespace(messages=messages, state=SimpleNamespace(get=state.get))
        return SimpleNamespace(stop_response=SimpleNamespace(stop_reason="end_turn", message=msg), agent=agent, retry=False)  # fmt: skip

    v.on_model_response(event("Te dije que antes de las 13:00, a las 12:45 te aviso."))
    last = event("Antes de las 13:00, aviso 12:45.")
    v.on_model_response(last)
    final = last.stop_response.message["content"][0]["text"]
    assert v.blocked_count == 1
    assert final.startswith("Para no darte una hora equivocada")
    assert (
        "Para lo que cocinaste a las 12:00: según U.S. FDA, cómelo antes de las 13:00 o deséchalo."
        in final
    )
    assert "12:45" not in final  # only the deadline, nothing else from memory


def test_follow_up_fallback_says_discard_when_the_deadline_passed(monkeypatch):
    from agent.hooks.verifier import VerifierHook

    monkeypatch.setenv("DEMO_MODE", "true")  # 12:00 > 11:30
    text = VerifierHook(language="en").safe_answer(_session_window(cooked="10:30", eat_by="11:30"))
    assert (
        "For the food you cooked at 10:30: according to U.S. FDA, the time limit has passed: throw it away now."
        in text
    )
    assert "11:30" not in text


def test_follow_up_fallback_skips_unknown_cooking_time(monkeypatch):
    from agent.hooks.verifier import VerifierHook

    monkeypatch.setenv("DEMO_MODE", "true")
    text = VerifierHook(language="es").safe_answer(_session_window(time_source="unknown"))
    assert "cocinaste" not in text and "13:00" not in text
