"""Tools in DEMO_MODE (fixtures, no network, no AWS)."""

import json
from types import SimpleNamespace

import pytest

from agent.tools import (
    check_danger_signs,
    compute_safe_window,
    get_forecast,
    plan_meals,
    plan_shelter_batches,
    schedule_reminder,
    track_outage,
)


def j(s):
    return json.loads(s)


def ctx(user_text: str = "", language: str = "en"):
    """Minimal stand-in for Strands ToolContext: .agent.messages and .agent.state (get/set)."""
    msgs = [{"role": "user", "content": [{"text": user_text}]}] if user_text else []
    state = {"session_id": "test-session", "language": language}
    return SimpleNamespace(
        agent=SimpleNamespace(
            messages=msgs, state=SimpleNamespace(get=state.get, set=state.__setitem__)
        )
    )


def test_forecast_demo_fixture():
    r = j(get_forecast())
    assert r["available"] and r["max_c"] == 38


def test_safe_window_tool_hot_demo_day():
    r = j(compute_safe_window(food_type="cooked_food", cooked_at="12:00", tool_context=ctx()))
    assert r["eat_by_hhmm"] == "13:00"
    assert r["unverified_rules_used"] is False  # all sources verified 2026-11-03


def test_outage_tool_bad_time():
    assert "error" in j(track_outage(outage_started_at="ayer", tool_context=ctx()))


def test_outage_tool_demo():
    r = j(
        track_outage(
            outage_started_at="06:00",
            fridge_door_opened=False,
            freezer_fullness="full",
            tool_context=ctx(),
        )
    )
    assert r["fridge_safe_until_hhmm"] == "10:00"


def test_shelter_tool_demo():
    r = j(
        plan_shelter_batches(
            people=120, service_windows=[["13:00", "15:00"]], dishes=["rice"], can_hot_hold=False
        )
    )
    assert len(r["batches"]) == 2


def test_meals_tool_no_times():
    assert "error" in j(plan_meals(people=3, meal_times=["x"], dishes=["beans"]))


def test_reminder_dry_run_without_infra(monkeypatch):
    monkeypatch.delenv("REMINDER_LAMBDA_ARN", raising=False)
    r = j(schedule_reminder(at="13:00", message="Eat the beans", tool_context=ctx()))
    assert r["dry_run"] is True and r["at_local"] == "13:00"


def test_danger_tool():
    r = j(check_danger_signs(answers={"CANNOT_DRINK": True}, country="MX"))
    assert r["escalate"] is True


def test_baby_rice_five_hours_ago_is_discard():
    """Regression: '5 hours ago' must never produce an eat-by time in the future."""
    r = j(
        compute_safe_window(
            food_type="cooked_rice", minutes_ago=300, audience="infant", tool_context=ctx()
        )
    )
    assert r["status"] == "discard_now"


def test_unknown_cooking_time_is_discard():
    r = j(compute_safe_window(food_type="cooked_food", tool_context=ctx()))
    assert r["status"] == "discard_now"


def test_user_text_wins_over_model_args():
    """Regression (diario 2026-11-03): model dropped '12:00' -> wrong 'discard now'."""
    r = j(
        compute_safe_window(
            food_type="cooked_food", tool_context=ctx("cocine frijoles a las 12:00")
        )
    )
    assert r["time_source"] == "user_text"
    assert r["eat_by_hhmm"] == "13:00"
    assert r["status"] == "eat_before_deadline"


def test_user_text_relative_time_baby_rice():
    r = j(
        compute_safe_window(
            food_type="cooked_rice",
            cooked_at="12:00",  # model got it wrong; user said 5 hours ago
            audience="infant",
            tool_context=ctx("¿Le doy a mi bebé el arroz de hace 5 horas?"),
        )
    )
    assert r["status"] == "discard_now"


def test_outage_reads_time_from_user_text():
    r = j(track_outage(tool_context=ctx("se fue la luz a las 06:00"), fridge_door_opened=False))
    assert r["fridge_safe_until_hhmm"] == "10:00"


def test_reminder_sms_needs_valid_number(monkeypatch):
    r = j(
        schedule_reminder(at="13:00", message="x", channel="sms", contact="123", tool_context=ctx())
    )
    assert r["scheduled"] is False


def test_request_context_overrides_demo_and_timezone():
    from agent.request_context import RequestSettings, set_current
    from agent.tools._common import tz

    set_current(RequestSettings(demo=False, timezone="Asia/Kolkata"))
    try:
        assert tz().key == "Asia/Kolkata"
        r = j(get_forecast())  # demo off and no location -> no forecast, worst case
        assert r["available"] is False
    finally:
        set_current(RequestSettings())


def test_invalid_timezone_falls_back_to_utc():
    from agent.request_context import RequestSettings, set_current
    from agent.tools._common import tz

    set_current(RequestSettings(timezone="../../etc/passwd"))
    try:
        assert tz().key == "UTC"
    finally:
        set_current(RequestSettings())


def test_reminder_time_and_text_come_from_rules_engine(monkeypatch):
    """Real bug (live smoke test): the model wrote "Eat the beans now, discard after" (no time)."""
    monkeypatch.delenv("REMINDER_LAMBDA_ARN", raising=False)
    c = ctx("cociné frijoles a las 12:00", language="es")
    w = j(compute_safe_window(food_type="cooked_food", tool_context=c))
    r = j(schedule_reminder(at="15:00", message="Eat the beans now, discard after", tool_context=c))
    assert r["at_local"] == w["reminder_at"][11:16]  # the model's 15:00 is ignored
    assert "13:00" in r["message"] and "FDA" in r["message"]
    assert r["message"].startswith("Al Tiempo: come la comida antes de las 13:00")
    assert r["summary"].startswith(f"Recordatorio programado para las {r['at_local']}")


def test_no_reminder_when_food_must_be_discarded(monkeypatch):
    monkeypatch.delenv("REMINDER_LAMBDA_ARN", raising=False)
    c = ctx("can I give my baby the rice I cooked 5 hours ago?")
    w = j(compute_safe_window(food_type="cooked_rice", audience="infant", tool_context=c))
    assert w["status"] == "discard_now"
    r = j(schedule_reminder(at="13:00", message="Eat the rice", tool_context=c))
    assert r["scheduled"] is False and "throw it away" in r["error"]


def test_outage_clears_dish_window(monkeypatch):
    monkeypatch.delenv("REMINDER_LAMBDA_ARN", raising=False)
    c = ctx("cociné frijoles a las 12:00")
    compute_safe_window(food_type="cooked_food", tool_context=c)
    track_outage(tool_context=c, outage_started_at="06:00", fridge_door_opened=False)
    r = j(schedule_reminder(at="09:45", message="Check the fridge", tool_context=c))
    assert r["at_local"] == "09:45" and r["message"] == "Check the fridge"


def test_safe_window_summary_is_built_in_code():
    """Live screenshot showed "I can set a reminder for 13:00" while the reminder was 12:45."""
    w = j(compute_safe_window(food_type="cooked_food", tool_context=ctx("I cooked beans at 12:00")))
    assert w["summary"] == (
        "According to U.S. FDA, eat it before 13:00 or throw it away. Above 32 °C (the forecast "
        "reaches 38 °C), the limit drops from 2 hours to 1. I can remind you at 12:45."
    )
    b = j(compute_safe_window(food_type="cooked_rice", audience="infant",
                              tool_context=ctx("rice I cooked 5 hours ago", language="es")))  # fmt: skip
    assert "ya pasó el límite: deséchalo ahora." in b["summary"]


@pytest.mark.parametrize(
    "text,door,freezer",
    [
        ("The power went out at 10:30. I kept the fridge closed. Freezer is half full.", False, "half"),
        ("The power went out at 06:00. I haven't opened the fridge and the freezer is full.", False, "full"),
        ("Se fue la luz a las 06:00, no he abierto el refri y el congelador está lleno.", False, "full"),
        ("se fue la luz, el refri sigue cerrado, el congelador a medias", False, "half"),
        ("se fue la luz y abrí el refri dos veces", True, None),
        ("the power went out at 7", None, None),
    ],
)  # fmt: skip
def test_outage_reads_door_and_freezer_from_user_text(text, door, freezer):
    from agent.tools.outage_tool import door_and_freezer_from_text

    assert door_and_freezer_from_text(text) == (door, freezer)


def test_outage_user_words_beat_missing_model_args():
    """Eval failure: user said "I kept the fridge closed", model passed nothing -> no 14:30."""
    c = ctx("The power went out at 10:30. I kept the fridge closed. Freezer is half full.")
    r = j(track_outage(tool_context=c))
    assert r["fridge_status"] == "ok" and "until 14:30" in r["summary"]["en"]
