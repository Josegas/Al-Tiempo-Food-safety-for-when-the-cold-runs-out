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
            people=120,
            service_windows=[["13:00", "15:00"]],
            dishes=["rice"],
            can_hot_hold=False,
            tool_context=ctx("Albergue con 120 personas, comida de 13:00 a 15:00"),
        )
    )
    assert len(r["batches"]) == 2


def test_meals_tool_no_times():
    assert "error" in j(
        plan_meals(people=3, meal_times=["x"], dishes=["beans"], tool_context=ctx())
    )


def test_meals_tool_rejects_invented_people_and_times():
    # "voy a hacer ensalada para el comedor": the user gave no times nor people
    r = j(
        plan_meals(
            people=10,
            meal_times=["12:00", "14:00"],
            dishes=["ensalada"],
            tool_context=ctx("voy a hacer ensalada de lechuga y jitomate para el comedor"),
        )
    )
    assert r["error"] == "not_said_by_user"
    assert set(r["missing"]) == {"people", "meal times"}


def test_meals_tool_accepts_user_numbers_in_words():
    r = j(
        plan_meals(
            people=4,
            meal_times=["13:30", "19:30"],
            dishes=["soup"],
            tool_context=ctx("Four of us. Lunch at 13:30 and dinner at 19:30"),
        )
    )
    assert len(r["meals"]) == 2


def test_shelter_tool_rejects_invented_window():
    r = j(
        plan_shelter_batches(
            people=150,
            service_windows=[["18:00", "20:00"]],
            dishes=["arroz"],
            can_hot_hold=False,
            tool_context=ctx("damos de comer a 150 personas de 1 a 4 de la tarde"),
        )
    )
    assert r["error"] == "not_said_by_user"


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
        "According to U.S. FDA, eat it before 13:00 or throw it away. In this heat (over 32 °C) "
        "bacteria grow faster: it lasts 1 hour, not 2. Shall I remind you at 12:45?"
    )
    b = j(compute_safe_window(food_type="cooked_rice", audience="infant",
                              tool_context=ctx("rice I cooked 5 hours ago", language="es")))  # fmt: skip
    assert "ya pasó el límite: lo más seguro es no comerlo y tirarlo." in b["summary"]
    assert "Sé que da lástima" in b["summary"]  # empathy + tip for next time


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


def test_reminder_turn_carries_the_engine_facts_it_is_based_on():
    """Live screenshot bug: in the "yes, schedule it" turn the model repeated "eat it before 13:00
    ... from 2 hours to 1" and the verifier blocked it, because only this turn's tool results count.
    The reminder result now carries the window it is based on, so those facts stay verifiable."""
    from agent.hooks.verifier import VerifierHook, collect_allowed

    c = ctx("I cooked beans at 12:00 and I have no fridge")
    compute_safe_window(food_type="cooked_food", tool_context=c)
    raw = schedule_reminder(at="12:45", message="x", tool_context=c)
    assert j(raw)["based_on"]["limit_hhmm"] == "13:00"
    times, minutes = collect_allowed(raw)
    assert {"12:45", "13:00"} <= times and {60, 120} <= minutes
    v = VerifierHook()  # the reminder result must not be mistaken for a safe window
    v.on_tool_result(type("E", (), {"result": {"content": [{"text": raw}]}})())
    assert v.last_window is None


def test_current_time_tool_in_simulated_mode(monkeypatch):
    """Live: "¿sabes qué hora es?" -> "no tengo acceso a la hora". Now a tool gives it."""
    from agent.tools.clock_tool import get_current_time

    monkeypatch.setenv("DEMO_MODE", "true")
    r = j(get_current_time(tool_context=ctx("¿qué hora es?", language="es")))
    assert r["now_hhmm"] == "12:00" and r["simulated"] is True and "demo clock" in r["note"]
    assert r["summary"] == "Son las 12:00 (reloj de la demo, no la hora real)."


def test_current_time_tool_in_real_mode(monkeypatch):
    from agent.hooks.verifier import collect_allowed
    from agent.tools.clock_tool import get_current_time

    monkeypatch.setenv("DEMO_MODE", "false")
    raw = get_current_time(tool_context=ctx("what time is it?"))
    r = j(raw)
    assert r["simulated"] is False and r["note"] == ""
    assert r["now_hhmm"] in collect_allowed(raw)[0]  # the verifier lets the model say it


def test_meals_tool_raw_salad_has_no_cooking_lead_time():
    r = j(
        plan_meals(
            people=40,
            meal_times=["14:00"],
            dishes=["ensalada de lechuga y jitomate"],
            tool_context=ctx("ensalada para el comedor, somos 40 personas y comemos a las 14:00"),
        )
    )
    assert r["raw_food"] is True
    assert r["meals"][0]["start_cooking_hhmm"] == "14:00"


def test_shelter_tool_accepts_split_service_window():
    # eval rw-23: "de 1 a 4 de la tarde" split by the model into three 1-hour windows
    r = j(
        plan_shelter_batches(
            people=150,
            service_windows=[["13:00", "14:00"], ["14:00", "15:00"], ["15:00", "16:00"]],
            dishes=["guisado"],
            can_hot_hold=False,
            tool_context=ctx("damos de comer a 150 personas de 1 a 4 de la tarde, no hay refri"),
        )
    )
    assert "error" not in r and r["batches"]


def test_shelter_summary_is_built_in_code_without_rule_ids():
    # live answer once said "According to FDA_HOT_1H": the plan is now worded in code
    r = j(
        plan_shelter_batches(
            people=120,
            service_windows=[["13:00", "15:00"]],
            dishes=["rice"],
            can_hot_hold=False,
            tool_context=ctx("Albergue con 120 personas, comida de 13:00 a 15:00", "es"),
        )
    )
    assert r["summary"].startswith(
        "Según U.S. FDA, plan para 120 personas: tanda 1: cocinar a las 12:00"
    )
    assert "tirar a las 14:00" in r["summary"] and "FDA_HOT_1H" not in r["summary"]
    from agent.hooks.verifier import collect_allowed, find_unbacked

    assert find_unbacked(r["summary"], *collect_allowed(json.dumps(r))) == {
        "times": [],
        "minutes": [],
    }
