from datetime import datetime, timedelta

import pytest


@pytest.fixture(autouse=True)
def _production_like(monkeypatch):
    # Production setting: unverified rules are NOT allowed. Demo fixtures, no network.
    monkeypatch.setenv("ALLOW_UNVERIFIED_RULES", "false")
    monkeypatch.setenv("DEMO_MODE", "true")


def flat(temp: float, start: datetime | None = None, hours: int = 24):
    start = start or datetime(2026, 11, 4, 0, 0)
    return [(start + timedelta(hours=h), temp) for h in range(hours)]
