"""Per-request settings (demo mode, time zone, location, session) shared with the tools.

Strands copies contextvars into its worker threads, so tools see the values of the request
that triggered them, even when several sessions run at the same time.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestSettings:
    demo: bool | None = None  # None -> use DEMO_MODE env var
    timezone: str | None = None  # IANA name from the browser, e.g. "America/Mazatlan"
    lat: float | None = None
    lon: float | None = None
    session_id: str | None = None


_DEFAULT = RequestSettings()
_CURRENT: ContextVar[RequestSettings | None] = ContextVar("al_tiempo_request", default=None)


def current() -> RequestSettings:
    return _CURRENT.get() or _DEFAULT


def set_current(settings: RequestSettings) -> None:
    _CURRENT.set(settings)
