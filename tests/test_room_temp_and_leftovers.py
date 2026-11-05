"""Room temperature the user reports (air conditioning), follow-ups keep the cooking time,
and the compost note for food that must be thrown away."""

from datetime import datetime, timedelta

import pytest

from agent import rules_engine as re_
from agent.forecast import _parse, load_fixture
from agent.leftovers import pick_leftover_tip
from agent.time_parse import extract_room_temp_c, latest_user_room_temp_c
from agent.tools.safe_window_tool import resolve_cooked_at, window_reason
from tests.conftest import flat

T0 = datetime(2026, 11, 4, 12, 0)
HOT = _parse(load_fixture("hot_day_38c"))


@pytest.mark.parametrize(
    "text,expected",
    [
        ("estaba en 22 grados de temperatura", 22.0),
        ("en el cuarto con aire acondicionado a 22 °C", 22.0),
        ("it's 72 degrees in the kitchen", 22.2),
        ("afuera hace 38 °C pero adentro 22 °C", 38.0),  # several -> the highest (safest)
        ("fue a las 3:55 pm", None),
        ("hace 2 horas", None),
        ("el horno a 180 grados", None),  # not an air temperature
    ],
)
def test_extract_room_temp(text, expected):
    assert extract_room_temp_c(text) == expected


def test_latest_room_temp_ignores_code_blocks_and_uses_newest():
    msgs = [
        {"role": "user", "content": [{"text": "el cuarto está a 22 grados"}]},
        {"role": "assistant", "content": [{"text": "ok"}]},
        {"role": "user", "content": [{"text": "pero estaba tapado"}, {"text": "[rules] 40 °C"}]},
    ]
    assert latest_user_room_temp_c(msgs) == 22.0


def test_user_room_temp_replaces_hot_forecast_but_never_beyond_2h():
    w = re_.compute_safe_window("cooked_food", T0, "general", HOT, room_temp_c=22)
    assert w.limit_minutes == 120  # 22 °C: no heat rule, but the 2-hour rule still applies
    assert w.temp_source == "user"
    cool = re_.compute_safe_window("cooked_food", T0, "general", flat(10), room_temp_c=5)
    assert cool.limit_minutes == 120  # a cool room never makes it longer than 2 hours


def test_user_room_temp_hot_keeps_1h():
    w = re_.compute_safe_window("cooked_food", T0, "general", flat(20), room_temp_c=35)
    assert w.limit_minutes == 60
    assert "FDA_HOT_1H" in w.rule_ids


@pytest.mark.parametrize("food,audience", [("cooked_rice", "general"), ("cooked_food", "infant")])
def test_user_room_temp_keeps_stricter_rules(food, audience):
    w = re_.compute_safe_window(food, T0, audience, HOT, room_temp_c=22)
    assert w.limit_minutes == 60


def test_reason_mentions_user_temperature():
    w = re_.compute_safe_window("cooked_food", T0, "general", HOT, room_temp_c=22).to_dict()
    assert "22 °C" in window_reason(w, "es")
    assert "2 horas" in window_reason(w, "es")


def test_followup_keeps_previous_cooking_time():
    now = datetime(2026, 11, 4, 18, 37)
    prev = datetime(2026, 11, 4, 15, 55)
    # "pero está con aire acondicionado a 22 grados": no time -> earlier time, not "120 min ago"
    cooked, src, _ = resolve_cooked_at("pero está a 22 grados", None, 120, now, prev)
    assert cooked == prev and src == "user_text"
    # a new time in the user's words still wins
    cooked, _, _ = resolve_cooked_at("fue a las 4:30 pm", None, None, now, prev)
    assert cooked.hour == 16 and cooked.minute == 30
    # no time in the user's words: the model's numbers are ignored -> unknown (the tool asks)
    cooked, src, _ = resolve_cooked_at("lo hice", "12:00", 60, now, None)
    assert cooked is None and src == "unknown"
    # an absolute time from an earlier user message still counts
    cooked, src, _ = resolve_cooked_at(
        "y estaba tapado", None, None, now, None, ["lo hice a las 5 pm"]
    )
    assert (cooked.hour, src) == (17, "user_text")
    assert timedelta  # imported for other tests


def test_leftover_tip_only_when_discard():
    assert (
        pick_leftover_tip({"kind": "safe_window", "status": "discard_now"}, "es")["id"] == "COMPOST"
    )
    assert pick_leftover_tip({"kind": "safe_window", "status": "eat_before_deadline"}, "es") is None
    assert pick_leftover_tip(None, "en") is None
    tip = pick_leftover_tip({"kind": "safe_window", "status": "discard_now"}, "en")
    assert "animal" not in tip["tip"].lower()  # never suggests feeding animals
    assert tip["source_url"].startswith("https://www.epa.gov/")
