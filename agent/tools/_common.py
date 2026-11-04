"""Shared helpers for tools: time parsing in the user's local time and JSON output."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from agent.forecast import demo_mode, load_fixture

DEMO_DATE = date.fromisoformat(load_fixture("hot_day_38c")["date"])


def tz() -> ZoneInfo:
    from agent.request_context import current

    name = current().timezone or os.getenv("DEFAULT_TIMEZONE", "America/Mazatlan")
    try:
        return ZoneInfo(name)
    except (KeyError, ValueError):  # unknown/invalid IANA name from a client
        return ZoneInfo("UTC")


def today() -> date:
    return DEMO_DATE if demo_mode() else datetime.now(tz()).date()


def now_local() -> datetime:
    """Naive local 'now' (demo mode: fixed at 12:00 on the demo day)."""
    if demo_mode():
        return datetime.combine(DEMO_DATE, time(12, 0))
    return datetime.now(tz()).replace(tzinfo=None, microsecond=0)


def parse_local(value: str | None, default: datetime | None = None) -> datetime | None:
    """Accepts 'HH:MM' (today) or ISO 'YYYY-MM-DDTHH:MM'. Returns naive local datetime."""
    if not value:
        return default
    value = value.strip()
    try:
        if "T" in value or len(value) > 5:
            dt = datetime.fromisoformat(value)
            return dt.astimezone(tz()).replace(tzinfo=None) if dt.tzinfo else dt
        hh, mm = value.split(":")
        return datetime.combine(today(), time(int(hh), int(mm)))
    except ValueError:
        return default


def out(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)
