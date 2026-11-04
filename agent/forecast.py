"""Hourly temperature forecast: Open-Meteo (no API key) or a demo fixture.

If the forecast fails, returns None and the rules engine assumes the worst case (> 32 °C).
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def demo_mode() -> bool:
    from agent.request_context import current

    req = current()
    if req.demo is not None:
        return req.demo
    return os.getenv("DEMO_MODE", "false").lower() == "true"


def _parse(payload: dict) -> list[tuple[datetime, float]]:
    times = payload["hourly"]["time"]
    temps = payload["hourly"]["temperature_2m"]
    return [
        (datetime.fromisoformat(t), float(v))
        for t, v in zip(times, temps, strict=True)
        if v is not None
    ]


def load_fixture(name: str = "hot_day_38c") -> dict:
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))


def get_hourly_temps(
    lat: float | None, lon: float | None, scenario: str = "hot_day_38c", timeout: float = 4.0
) -> tuple[list[tuple[datetime, float]] | None, str]:
    """Returns (hourly temps in local time, source label)."""
    if demo_mode():
        return _parse(load_fixture(scenario)), f"demo fixture '{scenario}'"
    if lat is None or lon is None:
        from agent.request_context import current

        lat, lon = current().lat, current().lon
    if lat is None or lon is None:
        return None, "no location given"
    query = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m",
            "timezone": "auto",
            "forecast_days": 2,
        }
    )
    try:
        with urllib.request.urlopen(f"{OPEN_METEO_URL}?{query}", timeout=timeout) as resp:  # noqa: S310
            return _parse(json.load(resp)), "Open-Meteo"
    except Exception as exc:  # network, timeout, bad JSON: fall back to worst case
        logger.warning("forecast_failed error=%s", exc)
        return None, "forecast unavailable"
