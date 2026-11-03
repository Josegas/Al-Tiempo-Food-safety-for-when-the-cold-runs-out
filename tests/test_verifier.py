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
