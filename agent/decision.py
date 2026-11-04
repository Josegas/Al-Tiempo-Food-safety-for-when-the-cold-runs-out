"""Structured "decision" for the web's safe-window timeline, copied from the rules engine output.

The web draws the timeline from these fields only (never from the model's text), so the picture
always matches the engine. Returns None when this turn did not compute a safe window.
"""

from __future__ import annotations

import json

FIELDS = ("food_type", "cooked_at_hhmm", "now_hhmm", "eat_by_hhmm", "status", "limit_minutes",
          "minutes_left", "serve_immediately")  # fmt: skip


def _short_source(window: dict) -> dict:
    src = window.get("deciding_source") or {}
    if src.get("kind") == "policy":
        return {"kind": "policy", "name": None}
    return {"kind": "official", "name": str(src.get("source_name", "")).split(" - ")[0] or None}


def safe_window_decision(new_messages: list[dict]) -> dict | None:
    """Last compute_safe_window result among this turn's messages, reduced to what the UI needs."""
    tool_ids = {
        b["toolUse"]["toolUseId"]
        for m in new_messages
        for b in m.get("content", [])
        if "toolUse" in b and b["toolUse"].get("name") == "compute_safe_window"
    }
    window = None
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
                if isinstance(data, dict) and "eat_by_hhmm" in data:
                    window = data
    if window is None:
        return None
    decision = {k: window.get(k) for k in FIELDS}
    decision["kind"] = "safe_window"
    decision["reminder_at_hhmm"] = str(window.get("reminder_at", ""))[11:16] or None
    decision["source"] = _short_source(window)
    # Cooking time unknown -> the engine assumed "long ago": don't draw a made-up start point.
    decision["cooked_known"] = window.get("time_source") != "unknown"
    return decision
