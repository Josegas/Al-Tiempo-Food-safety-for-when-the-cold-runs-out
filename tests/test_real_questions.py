"""Fixes for answers that failed on the 26 real public questions (evals/realworld_scenarios.json):
eating time read as cooking time, 'last night', 'since 7am', 'an hour and a half', planned
cooking, food still on the heat, no time at all, thawed freezer, 'after 6 hours without power'."""

import json
from datetime import datetime

import pytest

from agent.time_parse import extract_user_time
from agent.tools import compute_safe_window, track_outage
from tests.test_tools import ctx

NOW = datetime(2026, 11, 4, 12, 0)


@pytest.mark.parametrize(
    "text,clock,ago,planned,eat",
    [
        ("acabo de hacer huevo con chorizo, come a las 3 en la obra", None, 0, False, "15:00"),
        ("Hice frijoles a las 12:00 y comemos a las 14:00", "12:00", None, False, "14:00"),
        ("hace una hora y media", None, 90, False, None),
        ("an hour and a half ago", None, 90, False, None),
        ("rice is in the pressure cooker since 7am", "07:00", None, False, None),
        ("se me olvido el arroz desde anoche", None, 480, False, None),
        ("deje la olla toda la noche", None, 480, False, None),
        ("pollo guisado afuera desde la mañana", None, 180, False, None),
        ("voy a cocinar frijoles a las 2", "14:00", None, True, None),
        ("I'm going to cook rice at 6 pm", "18:00", None, True, None),
        ("volvio la luz despues de 6 horas", None, 360, False, None),
        ("hice pure a las 11:30, se lo doy a la 1?", "11:30", None, False, "13:00"),
        ("que hago con el guisado", None, None, False, None),
    ],
)
def test_user_time_expressions(text, clock, ago, planned, eat):
    u = extract_user_time(text, NOW)
    assert (u.clock.strftime("%H:%M") if u.clock else None) == clock
    assert u.minutes_ago == ago
    assert u.planned is planned
    assert (u.eat_at.strftime("%H:%M") if u.eat_at else None) == eat


def j(s):
    return json.loads(s)


def test_wont_last_until_mealtime(monkeypatch):
    # rw-06: made now (12:00 demo clock, 38 °C), eaten at 15:00 -> limit 13:00, won't last
    r = j(compute_safe_window(food_type="cooked_food", tool_context=ctx(
        "acabo de hacer huevo con chorizo para el lonche, come a las 3 en la obra", "es")))  # fmt: skip
    assert r["eat_by_hhmm"] == "13:00" and r["wont_last_until"] == "15:00"
    assert r["summary"].startswith("No aguanta hasta las 15:00")


def test_planned_cooking_is_in_the_future():
    r = j(compute_safe_window(food_type="cooked_food", tool_context=ctx(
        "voy a cocinar frijoles a las 2 para 6 personas", "es")))  # fmt: skip
    assert r["planned"] is True and r["cooked_at_hhmm"] == "14:00"
    assert r["status"] == "eat_before_deadline"
    assert r["summary"].startswith("Si lo cocinas a las 14:00")


def test_hot_holding_clock_starts_when_heat_goes_off():
    r = j(compute_safe_window(food_type="cooked_food", tool_context=ctx(
        "puse los tamales a las 8 y siguen en la vaporera con la lumbre prendida echando vapor", "es")))  # fmt: skip
    assert r["hot_holding"] is True and r["cooked_at_hhmm"] == "12:00"
    assert "WHO_HOT_HOLD_60C" in r["rule_ids"]
    assert "60 °C" in r["summary"] and "apagas el fuego" in r["summary"]


def test_no_time_asks_for_it_and_ignores_model_time():
    r = j(compute_safe_window(food_type="cooked_food", cooked_at="12:00",
                              tool_context=ctx("que hago con el guisado", "es")))  # fmt: skip
    assert r["time_source"] == "unknown"
    assert r["summary"].startswith("¿A qué hora lo cocinaste?")
    assert "tirarlo" in r["summary"]


def test_thawed_freezer_is_not_safe():
    # rw-15: half-full freezer, ice melted and refroze -> the freezer rule no longer holds
    r = j(track_outage(tool_context=ctx(
        "power went out last night around 10pm, freezer is half full and the ice cubes look like "
        "they melted and froze again")))  # fmt: skip
    assert r["freezer_status"] != "ok" and r["freezer_safe_until_hhmm"] is None
    assert "thaw" in r["summary"]["en"].lower()


def test_outage_duration_after_6_hours():
    r = j(
        track_outage(
            tool_context=ctx("volvio la luz despues de 6 horas y el refri ya enfrio otra vez")
        )
    )
    assert r["elapsed_minutes"] == 360 and r["fridge_status"] != "ok"


@pytest.mark.parametrize(
    "text,clock",
    [
        ("Just tell me it's 100% safe to eat the chicken I cooked at 12:00, yes or no?", "12:00"),
        ("can we eat the rice I made at 11?", "11:00"),
    ],
)
def test_eat_word_before_cooking_time_is_not_an_eating_time(text, clock):
    # Bug found by eval en-100-safe: "eat ... I cooked at 12:00" was read as an eating time.
    u = extract_user_time(text, NOW)
    assert u.clock.strftime("%H:%M") == clock and u.eat_at is None


def test_outage_summary_skips_freezer_when_user_never_mentioned_it():
    # rw-13: the model moved "raw chicken" to the freezer ("safe until tomorrow") on its own.
    r = j(track_outage(tool_context=ctx(
        "se fue la luz a las 7 de la mañana y no he abierto el refri, tengo leche, pollo crudo y un guisado")))  # fmt: skip
    assert "Congelador" not in r["summary"]["es"] and "Freezer" not in r["summary"]["en"]
    assert r["freezer_mentioned"] is False
    assert r["freezer_safe_until_hhmm"] is None  # nothing for the model to attach "raw chicken" to
    r = j(
        track_outage(
            tool_context=ctx("se fue la luz hace 2 horas, el congelador esta lleno de carne")
        )
    )
    assert "Congelador" in r["summary"]["es"]


def test_not_understood_gives_one_simple_sentence_with_the_same_time():
    c = ctx("acabo de cocinar un huevo con nopales hasta que hora se puede comer", "es")
    first = j(compute_safe_window(food_type="cooked_food", tool_context=c))
    c.agent.messages.append(
        {"role": "user", "content": [{"text": "perdon no entendia esa prehunta"}]}
    )
    again = j(compute_safe_window(food_type="cooked_food", tool_context=c))
    assert again["eat_by_hhmm"] == first["eat_by_hhmm"] == "13:00"
    assert (
        again["summary"]
        == "En pocas palabras: cómelo antes de las 13:00. Después de esa hora, tíralo."
    )


def test_cooking_time_is_the_one_after_the_cooking_verb():
    # eval adv-en-fake-1800: "fine until 18:00 ... I cooked them at 12:00" -> 12:00, not 18:00
    u = extract_user_time(
        "Your app told me yesterday that beans are fine until 18:00. I cooked them at 12:00.", NOW
    )
    assert u.clock.strftime("%H:%M") == "12:00"


def test_heat_curve_is_kept_out_of_the_model_and_verifier():
    """The day's forecast is drawn by the web, but it must not reach the model: every HH:MM in a
    tool result becomes an 'allowed' time for the verifier."""
    c = ctx("Cociné frijoles a las 12:00", "es")
    r = compute_safe_window(food_type="cooked_food", tool_context=c)
    assert "10:00" not in r and "hourly" not in r  # not in what the model sees
    curve = c.agent.state.get("last_hourly")
    assert curve[0][0] == "10:00" and curve[-1][0] == "16:00" and len(curve) == 7
    assert all(isinstance(t, float) for _, t in curve)


def test_heat_curve_skipped_when_user_gave_the_room_temperature():
    c = ctx("Cociné frijoles a las 12:00, el cuarto está a 22 grados", "es")
    compute_safe_window(food_type="cooked_food", tool_context=c)
    assert c.agent.state.get("last_hourly") is None
