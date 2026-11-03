"""Tools in DEMO_MODE (fixtures, no network, no AWS)."""

import json
from types import SimpleNamespace

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


def ctx(user_text: str = ""):
    """Minimal stand-in for Strands ToolContext: only .agent.messages is used."""
    msgs = [{"role": "user", "content": [{"text": user_text}]}] if user_text else []
    return SimpleNamespace(agent=SimpleNamespace(messages=msgs))


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
    r = j(schedule_reminder(at="13:00", message="Eat the beans"))
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
