from datetime import datetime, timedelta

import pytest


@pytest.fixture(autouse=True)
def _allow_unverified(monkeypatch):
    # Tests check the LOGIC. Source verification is enforced separately by scripts/check_rules.py.
    monkeypatch.setenv("ALLOW_UNVERIFIED_RULES", "true")
    monkeypatch.setenv("DEMO_MODE", "true")


def flat(temp: float, start: datetime | None = None, hours: int = 24):
    start = start or datetime(2026, 11, 4, 0, 0)
    return [(start + timedelta(hours=h), temp) for h in range(hours)]
