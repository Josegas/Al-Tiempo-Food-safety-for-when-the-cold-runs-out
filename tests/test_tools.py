"""Tools in DEMO_MODE (fixtures, no network, no AWS)."""

import json

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


def test_forecast_demo_fixture():
    r = j(get_forecast())
    assert r["available"] and r["max_c"] == 38


def test_safe_window_tool_hot_demo_day():
    r = j(compute_safe_window(food_type="cooked_food", cooked_at="12:00"))
    assert r["eat_by_hhmm"] == "13:00"
    assert r["unverified_rules_used"] is True  # until sources are verified


def test_outage_tool_bad_time():
    assert "error" in j(track_outage(outage_started_at="ayer"))


def test_outage_tool_demo():
    r = j(
        track_outage(outage_started_at="06:00", fridge_door_opened=False, freezer_fullness="full")
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
    r = j(compute_safe_window(food_type="cooked_rice", minutes_ago=300, audience="infant"))
    assert r["status"] == "discard_now"


def test_unknown_cooking_time_is_discard():
    r = j(compute_safe_window(food_type="cooked_food"))
    assert r["status"] == "discard_now"
