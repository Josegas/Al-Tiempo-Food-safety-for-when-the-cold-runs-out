import dataclasses
import json
from datetime import datetime

import pytest

from agent import rules_engine as re_
from agent.forecast import _parse, load_fixture
from tests.conftest import flat

T0 = datetime(2026, 11, 4, 12, 0)


# --- safe window: boundaries ---------------------------------------------------
def test_mild_day_two_hours():
    w = re_.compute_safe_window("cooked_food", T0, "general", flat(25))
    assert w.limit_minutes == 120
    assert w.eat_by_hhmm == "14:00"
    assert "FDA_HOT_1H" not in w.rule_ids


def test_exactly_32c_is_not_above_threshold():
    w = re_.compute_safe_window("cooked_food", T0, "general", flat(32.0))
    assert w.limit_minutes == 120


def test_just_above_32c_one_hour():
    w = re_.compute_safe_window("cooked_food", T0, "general", flat(32.1))
    assert w.limit_minutes == 60
    assert w.eat_by_hhmm == "13:00"
    assert "FDA_HOT_1H" in w.rule_ids


def test_heat_later_in_window_counts():
    temps = [(datetime(2026, 11, 4, h), 30.0 if h < 13 else 35.0) for h in range(24)]
    w = re_.compute_safe_window("cooked_food", T0, "general", temps)
    assert w.limit_minutes == 60


def test_missing_forecast_assumes_worst_case():
    w = re_.compute_safe_window("cooked_food", T0, "general", None)
    assert w.limit_minutes == 60
    assert any("assumed hot" in a for a in w.assumptions)


def test_unknown_food_treated_as_cooked_food():
    w = re_.compute_safe_window(None, T0, None, flat(20))
    assert w.food_type == "cooked_food"
    assert w.limit_minutes == 120


def test_rice_one_hour_even_on_mild_day():
    w = re_.compute_safe_window("cooked_rice", T0, "general", flat(20))
    assert w.limit_minutes == 60
    assert "NHS_RICE_1H" in w.rule_ids


def test_hot_day_fixture_38c():
    temps = _parse(load_fixture("hot_day_38c"))
    w = re_.compute_safe_window("cooked_food", T0, "general", temps)
    assert w.limit_minutes == 60


# --- strict mode for children ------------------------------------------------
@pytest.mark.parametrize("audience", ["infant", "young_child"])
def test_children_strict_mode(audience):
    w = re_.compute_safe_window("cooked_food", T0, audience, flat(20))
    assert w.limit_minutes == 60
    assert w.serve_immediately is True
    assert w.keep_leftovers is False
    assert "POLICY_CHILD_STRICT" in w.rule_ids


def test_formula_feeding_started_uses_earliest_deadline():
    prepared = datetime(2026, 11, 4, 12, 0)
    feeding = datetime(2026, 11, 4, 12, 30)
    w = re_.compute_safe_window("infant_formula", prepared, "infant", flat(20), feeding)
    # strict policy (12:00 + 60) is earlier than feeding rule (12:30 + 60)
    assert w.eat_by_hhmm == "13:00"
    assert w.keep_leftovers is False


def test_never_longer_than_two_hours():
    for temp in (0, 15, 25, 32, 40):
        for food in ("cooked_food", "cooked_rice", "infant_formula", "x"):
            for aud in ("general", "infant", "young_child"):
                w = re_.compute_safe_window(food, T0, aud, flat(temp))
                assert w.limit_minutes <= 120


def test_reminder_before_deadline():
    w = re_.compute_safe_window("cooked_food", T0, "general", flat(25))
    assert w.reminder_at < w.eat_by


# --- unverified rules are blocked unless explicitly allowed --------------------
def test_unverified_rule_blocked_in_production(monkeypatch):
    rules = dict(re_.load_rules())
    rules["WHO_COOKED_2H"] = dataclasses.replace(rules["WHO_COOKED_2H"], unverified=True)
    monkeypatch.setattr(re_, "load_rules", lambda: rules)
    with pytest.raises(re_.RuleNotAllowedError):
        re_.compute_safe_window("cooked_food", T0, "general", flat(25))
    monkeypatch.setenv("ALLOW_UNVERIFIED_RULES", "true")  # dev override works
    assert re_.compute_safe_window("cooked_food", T0, "general", flat(25)).unverified_rules_used


def test_all_rules_verified_with_verbatim_text():
    import yaml

    raw = yaml.safe_load((re_.RULES_DIR / "food_rules.yaml").read_text(encoding="utf-8"))["rules"]
    for r in raw:
        assert r["unverified"] is False, r["id"]
        assert r.get("verified_text"), r["id"]


def test_every_rule_has_source():
    for rule in re_.load_rules().values():
        assert rule.source_url.startswith("https://")
        assert rule.source_name
        if not rule.unverified:
            assert rule.verified_on


# --- outage mode -------------------------------------------------------------------
def test_outage_fridge_ok_before_4h_door_closed():
    r = re_.track_outage(datetime(2026, 11, 4, 6), datetime(2026, 11, 4, 9, 59), False, "full")
    assert r["fridge_status"] == "ok"
    assert r["fridge_safe_until_hhmm"] == "10:00"


def test_outage_fridge_exactly_4h_not_ok():
    r = re_.track_outage(datetime(2026, 11, 4, 6), datetime(2026, 11, 4, 10, 0), False, "full")
    assert r["fridge_status"] != "ok"


def test_outage_door_opened_is_conservative():
    r = re_.track_outage(datetime(2026, 11, 4, 6), datetime(2026, 11, 4, 7), True, "full")
    assert r["fridge_status"] != "ok"


def test_outage_unknown_freezer_assumes_half():
    r = re_.track_outage(datetime(2026, 11, 4, 6), datetime(2026, 11, 4, 7), False, None)
    assert "FDA_OUTAGE_FREEZER_HALF_24H" in r["rule_ids"]
    assert r["freezer_safe_until"] == "2026-11-05T06:00:00"


def test_outage_full_freezer_48h():
    r = re_.track_outage(datetime(2026, 11, 4, 6), datetime(2026, 11, 5, 7), False, "full")
    assert r["freezer_status"] == "ok"


# --- shelter batches ---------------------------------------------------------------
def test_shelter_hot_day_no_hot_hold_120_people():
    w = (datetime(2026, 11, 4, 13), datetime(2026, 11, 4, 15))
    plan = re_.plan_shelter_batches(120, [w], ["rice"], False, flat(38))
    assert len(plan["batches"]) == 2  # 2 h service / 1 h limit
    assert all(b["portions"] == 60 for b in plan["batches"])
    assert [b["ready_hhmm"] for b in plan["batches"]] == ["13:00", "14:00"]
    assert [b["discard_hhmm"] for b in plan["batches"]] == ["14:00", "15:00"]


def test_shelter_partial_hour_rounds_up_batches():
    w = (datetime(2026, 11, 4, 19), datetime(2026, 11, 4, 20, 30))
    plan = re_.plan_shelter_batches(120, [w], ["beans"], False, flat(38))
    assert len(plan["batches"]) == 2
    assert sum(b["portions"] for b in plan["batches"]) >= 120


def test_shelter_hot_hold_single_batch():
    w = (datetime(2026, 11, 4, 13), datetime(2026, 11, 4, 15))
    plan = re_.plan_shelter_batches(120, [w], ["stew"], True, flat(38))
    assert len(plan["batches"]) == 1
    assert plan["batches"][0]["keep_above_c"] == 60
    assert "WHO_HOT_HOLD_60C" in plan["rule_ids"]


def test_shelter_invalid_inputs():
    with pytest.raises(ValueError):
        re_.plan_shelter_batches(0, [(T0, T0)], [], False)
    with pytest.raises(ValueError):
        re_.plan_shelter_batches(10, [(T0, T0)], [], False)


def test_no_batch_served_beyond_its_limit():
    w = (datetime(2026, 11, 4, 11), datetime(2026, 11, 4, 16, 10))
    for temp in (20, 38):
        plan = re_.plan_shelter_batches(50, [w], ["x"], False, flat(temp))
        limit = 60 if temp > 32 else 120
        for b in plan["batches"]:
            span = datetime.fromisoformat(b["discard_at"]) - datetime.fromisoformat(b["ready_at"])
            assert span.total_seconds() / 60 <= limit


# --- meals ---------------------------------------------------------------------------
def test_plan_meals_hot_day():
    plan = re_.plan_meals(4, [datetime(2026, 11, 4, 14)], ["beans"], flat(38))
    meal = plan["meals"][0]
    assert meal["start_cooking_hhmm"] == "13:00"
    assert meal["eat_by_hhmm"] == "15:00"


def test_plan_meals_child_strict():
    plan = re_.plan_meals(4, [datetime(2026, 11, 4, 14)], ["rice"], flat(20), audience="infant")
    assert plan["meals"][0]["eat_by_hhmm"] == "15:00"


# --- danger signs ------------------------------------------------------------------
NO = {
    k: False
    for k in ["LETHARGIC", "SUNKEN_EYES", "CANNOT_DRINK", "SKIN_PINCH_SLOW", "BLOOD_IN_STOOL"]
}


def test_no_signs_no_escalation():
    assert re_.check_danger_signs(NO, "MX")["escalate"] is False


@pytest.mark.parametrize("sign", list(NO))
def test_any_single_sign_escalates(sign):
    r = re_.check_danger_signs({**NO, sign: True}, "MX")
    assert r["escalate"] is True
    assert r["emergency_number"] == "911"


def test_unknown_answer_escalates():
    r = re_.check_danger_signs({**NO, "SUNKEN_EYES": None}, "IN")
    assert r["escalate"] is True
    assert r["emergency_number"] == "112"


def test_unknown_country_generic_message():
    r = re_.check_danger_signs({**NO, "LETHARGIC": True}, "ZZ")
    assert r["message_id"] == "ESCALATE_LOCAL_EMERGENCY"
    assert r["emergency_number"] is None


# --- status at "now" (real bug found in smoke test, see docs/diario.md) -------------
def test_status_discard_now_when_past_deadline():
    w = re_.compute_safe_window(
        "cooked_rice", datetime(2026, 11, 4, 7), "infant", flat(38), now=datetime(2026, 11, 4, 12)
    )
    assert w.status == "discard_now"
    assert w.minutes_left == 0


def test_status_eat_before_deadline():
    w = re_.compute_safe_window("cooked_food", T0, "general", flat(25), now=T0)
    assert w.status == "eat_before_deadline"
    assert w.minutes_left == 120


def test_outage_summary_after_fridge_limit_says_discard():
    """Real bug (live demo): the model said "you have until 10:00" when it was already 12:00."""
    r = re_.track_outage(datetime(2026, 11, 4, 6), datetime(2026, 11, 4, 12), False, "full")
    assert "ended at 10:00" in r["summary"]["en"] and "Throw away" in r["summary"]["en"]
    assert "terminó a las 10:00" in r["summary"]["es"]
    assert "until Friday 06:00" in r["summary"]["en"]  # 48 h later, with the day
    assert "viernes a las 06:00" in r["summary"]["es"]


def test_outage_summary_before_limit_door_closed():
    r = re_.track_outage(datetime(2026, 11, 4, 6), datetime(2026, 11, 4, 9), False, "half")
    assert "until 10:00" in r["summary"]["en"] and "until tomorrow 06:00" in r["summary"]["en"]
    assert "hasta mañana a las 06:00" in r["summary"]["es"]  # not "hasta el mañana"


def test_outage_door_opened_gives_no_fridge_deadline():
    """Eval bug: with the door opened the model still said "safe until 15:00" (the engine's
    unused deadline). No rule applies, so no time is returned and the verifier blocks any."""
    r = re_.track_outage(datetime(2026, 11, 4, 11), datetime(2026, 11, 4, 12), True, "full")
    assert r["fridge_safe_until_hhmm"] is None and r["freezer_safe_until_hhmm"] is None
    assert "15:00" not in json.dumps(r)
    closed = re_.track_outage(datetime(2026, 11, 4, 11), datetime(2026, 11, 4, 12), False, "full")
    assert closed["fridge_safe_until_hhmm"] == "15:00"
