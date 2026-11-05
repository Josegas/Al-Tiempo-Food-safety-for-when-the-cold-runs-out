"""Structured "decision" for the web's safe-window timeline, copied from the rules engine output.

The web draws the timeline from these fields only (never from the model's text), so the picture
always matches the engine. Returns None when this turn did not compute a safe window.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from agent.rules_engine import comprehension_options

FIELDS = ("food_type", "cooked_at_hhmm", "now_hhmm", "eat_by_hhmm", "status", "limit_minutes",
          "minutes_left", "serve_immediately", "planned", "hot_holding", "wont_last_until")  # fmt: skip


def _short_source(window: dict) -> dict:
    src = window.get("deciding_source") or {}
    if src.get("kind") == "policy":
        return {"kind": "policy", "name": None}
    return {"kind": "official", "name": str(src.get("source_name", "")).split(" - ")[0] or None}


def _last_tool_result(new_messages: list[dict], tool_name: str, key: str) -> dict | None:
    """Last successful JSON result of `tool_name` in this turn that contains `key`."""
    tool_ids = {
        b["toolUse"]["toolUseId"]
        for m in new_messages
        for b in m.get("content", [])
        if "toolUse" in b and b["toolUse"].get("name") == tool_name
    }
    found = None
    for m in new_messages:
        for b in m.get("content", []):
            res = b.get("toolResult")
            if not res or res.get("toolUseId") not in tool_ids or res.get("status") == "error":
                continue
            for c in res.get("content", []):
                try:
                    data = json.loads(c.get("text", ""))
                except ValueError:
                    continue
                if isinstance(data, dict) and key in data:
                    found = data
    return found


def safe_window_decision(new_messages: list[dict]) -> dict | None:
    """Last compute_safe_window result among this turn's messages, reduced to what the UI needs."""
    window = _last_tool_result(new_messages, "compute_safe_window", "eat_by_hhmm")
    if window is None:
        return None
    decision = {k: window.get(k) for k in FIELDS}
    decision["kind"] = "safe_window"
    decision["reminder_at_hhmm"] = str(window.get("reminder_at", ""))[11:16] or None
    decision["source"] = _short_source(window)
    decision["rule_id"] = (window.get("deciding_source") or {}).get("rule_id")
    decision["max_temp_c"] = window.get("max_temp_c")
    decision["hot_threshold_c"] = window.get("hot_threshold_c")
    decision["temp_source"] = window.get("temp_source") or "forecast"
    # Cooking time unknown -> the engine assumed "long ago": don't draw a made-up start point.
    decision["cooked_known"] = window.get("time_source") != "unknown"
    # Comprehension check: built here, outside the model loop, so the distractor times never
    # reach the model or the verifier's list of allowed times.
    quiz = None
    if decision["status"] == "eat_before_deadline" and decision["cooked_known"]:
        try:
            eat_by = datetime.fromisoformat(str(window.get("eat_by")))
            left = window.get("minutes_left")
            now = eat_by - timedelta(minutes=left) if isinstance(left, int) else None
            quiz = comprehension_options(eat_by, now)
        except ValueError:
            quiz = None
    decision["quiz"] = quiz
    return decision


def shelter_plan_decision(new_messages: list[dict]) -> dict | None:
    """Last plan_shelter_batches result of this turn, reduced to what the batch timeline needs.

    Every time is copied from the engine output (never parsed from the model's text).
    """
    plan = _last_tool_result(new_messages, "plan_shelter_batches", "batches")
    if plan is None or not plan.get("batches"):
        return None
    batches = [
        {
            "start_cooking_hhmm": str(b.get("start_cooking", ""))[11:16] or None,
            "ready_hhmm": b.get("ready_hhmm"),
            "discard_hhmm": b.get("discard_hhmm"),
            "portions": b.get("portions"),
            "keep_above_c": b.get("keep_above_c"),
            "dishes": b.get("dishes") or [],
        }
        for b in plan["batches"]
    ]
    sources = plan.get("sources") or []
    official = [s for s in sources if s.get("kind") != "policy"]
    return {
        "kind": "shelter_plan",
        "people": plan.get("people"),
        "service_windows": plan.get("service_windows") or [],
        "batches": batches,
        "hot_hold": any(b["keep_above_c"] is not None for b in batches),
        "rule_ids": plan.get("rule_ids") or [],
        "source": {
            "kind": "official" if official else "policy",
            "name": str(official[0].get("source_name", "")).split(" - ")[0] if official else None,
        },
    }
