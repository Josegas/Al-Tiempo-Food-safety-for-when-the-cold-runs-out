"""Deterministic extraction of times the USER wrote (es/en). The LLM never decides these.

"cociné frijoles a las 12:00"      -> clock 12:00
"a las 2 de la tarde" / "at 2 pm"  -> clock 14:00
"a las 3 y media de la tarde"      -> clock 15:30
"hace 5 horas" / "5 hours ago"     -> 300 minutes ago
"hace media hora" / "an hour ago"  -> 30 / 60 minutes ago
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

_NUM_WORDS = {
    "un": 1, "una": 1, "uno": 1, "a": 1, "an": 1, "one": 1,
    "dos": 2, "two": 2, "tres": 3, "three": 3, "cuatro": 4, "four": 4,
    "cinco": 5, "five": 5, "seis": 6, "six": 6,
}  # fmt: skip
_NUM = r"(\d+(?:[.,]\d+)?|" + "|".join(_NUM_WORDS) + r")"

AGO_ES = re.compile(r"\bhace\s+" + _NUM + r"\s*(horas?|hrs?|h|minutos?|mins?)\b", re.I)
AGO_EN = re.compile(r"\b" + _NUM + r"\s*(hours?|hrs?|h|minutes?|mins?)\s+ago\b", re.I)
HALF_HOUR = re.compile(r"\b(hace\s+media\s+hora|half\s+an\s+hour\s+ago)\b", re.I)
JUST_NOW = re.compile(r"\b(ahorita|reci[eé]n|acabo\s+de|just\s+now|just\s+(cooked|made))\b", re.I)

_HOUR_WORDS = {
    "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
    "nueve": 9, "diez": 10, "once": 11, "doce": 12, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}  # fmt: skip
_SUFFIX = (
    r"([ap]\.?\s?m\.?|(?:de|en)\s+la\s+(?:mañana|tarde|noche)"
    r"|in\s+the\s+(?:morning|afternoon|evening))?"
)
# 12:00, 2:30 pm, 14h30, 3:30 de la tarde
CLOCK = re.compile(r"\b(\d{1,2})[:h](\d{2})\s*" + _SUFFIX, re.I)
# "a las 12", "a la 1 de la tarde", "a las 3 y media de la tarde", "a las tres y cuarto",
# "a las 2 menos cuarto", "a las 4 y 20", "at 2 pm", "at 7"
CLOCK_WORDS = re.compile(
    r"\b(?:a\s+las?|at)\s+(\d{1,2}|" + "|".join(_HOUR_WORDS) + r")\b"
    r"(?:\s+(y\s+media|y\s+cuarto|menos\s+cuarto|y\s+\d{1,2})(?:\s*min(?:utos)?\b)?)?"
    r"(?!\s*(?:horas?|hours?|min))\s*" + _SUFFIX,
    re.I,
)
NOON = re.compile(r"\b(al\s+mediod[ií]a|at\s+noon)\b", re.I)


def _fraction(hh: int, frac: str | None) -> tuple[int, int]:
    """'y media' -> :30, 'y cuarto' -> :15, 'menos cuarto' -> one hour earlier :45, 'y 20' -> :20."""
    if not frac:
        return hh, 0
    f = " ".join(frac.lower().split())
    if f == "y media":
        return hh, 30
    if f == "y cuarto":
        return hh, 15
    if f == "menos cuarto":
        return (hh - 1) % 24 or 12, 45
    return hh, int(f.split()[-1])


@dataclass
class UserTime:
    clock: datetime | None = None
    minutes_ago: int | None = None
    assumption: str | None = None


def _resolve_clock(hh: int, mm: int, suffix: str | None, now: datetime) -> UserTime:
    """Most recent PAST moment matching the time. 'a las 2' at 15:00 -> 14:00 today."""
    candidates = [_to_24h(hh, suffix)] if suffix or hh == 0 or hh > 12 else [hh % 12, hh % 12 + 12]
    past = []
    for h in candidates:
        t = now.replace(hour=h, minute=mm, second=0, microsecond=0)
        if t > now:
            t -= timedelta(days=1)
        past.append(t)
    clock = max(past)
    note = None
    if len(candidates) > 1:
        note = f"Time without am/pm: assumed {clock.strftime('%H:%M')} (most recent)."
    if clock.date() < now.date():
        note = (note or "") + f" Assumed yesterday ({clock.strftime('%Y-%m-%d %H:%M')})."
    return UserTime(clock=clock, assumption=note.strip() if note else None)


def _num(token: str) -> float:
    token = token.lower()
    return float(_NUM_WORDS[token]) if token in _NUM_WORDS else float(token.replace(",", "."))


def _to_24h(h: int, suffix: str | None) -> int:
    if not suffix:
        return h
    s = suffix.lower()
    pm = s.startswith("p") or "tarde" in s or "noche" in s or "afternoon" in s or "evening" in s
    if pm and h < 12:
        return h + 12
    if not pm and h == 12:
        return 0
    return h


def extract_user_time(text: str, now: datetime) -> UserTime:
    """Most explicit expression wins: relative ('5 hours ago') > clock time > 'just now'."""
    for rx in (AGO_ES, AGO_EN):
        m = rx.search(text)
        if m:
            value, unit = _num(m.group(1)), m.group(2).lower()
            minutes = value * 60 if unit.startswith("h") else value
            return UserTime(minutes_ago=int(round(minutes)))
    if HALF_HOUR.search(text):
        return UserTime(minutes_ago=30)

    hh = mm = None
    suffix = None
    m = CLOCK.search(text)
    if m:
        hh, mm, suffix = int(m.group(1)), int(m.group(2)), m.group(3)
    else:
        m = CLOCK_WORDS.search(text)
        if m:
            tok = m.group(1).lower()
            hour = _HOUR_WORDS[tok] if tok in _HOUR_WORDS else int(tok)
            hh, mm = _fraction(hour, m.group(2))
            suffix = m.group(3)
        elif NOON.search(text):
            hh, mm, suffix = 12, 0, "pm"
    if hh is not None and hh < 24 and mm < 60:
        return _resolve_clock(hh, mm, suffix, now)

    if JUST_NOW.search(text):
        return UserTime(minutes_ago=0)
    return UserTime()


def last_user_text(messages: list) -> str:
    """Text of the most recent user message (ignores tool results)."""
    for msg in reversed(messages or []):
        if msg.get("role") != "user":
            continue
        texts = [b["text"] for b in msg.get("content", []) if "text" in b]
        texts = [t for t in texts if not t.startswith("[verifier]")]
        if texts:
            return " ".join(texts)
    return ""
