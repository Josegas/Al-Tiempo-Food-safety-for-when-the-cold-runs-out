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

AGO_ES = re.compile(
    r"\bhace\s+(?:como\s+|unas?\s+|casi\s+|m[aá]s\s+de\s+)?"
    + _NUM
    + r"\s*(horas?|hrs?|h|minutos?|mins?)\b(\s+y\s+media)?",
    re.I,
)
AGO_EN = re.compile(
    r"\b"
    + _NUM
    + r"(\s+and\s+a\s+half)?\s*(hours?|hrs?|h|minutes?|mins?)(\s+and\s+a\s+half)?\s+ago\b",
    re.I,
)
# Durations without "ago": "después de 6 horas", "after 6 hours", "6 horas sin luz", "for 6 hours"
DURATION = re.compile(
    r"\b(?:despu[eé]s\s+de|durante|por|after|for)\s+" + _NUM + r"\s*(horas?|hours?|hrs?)\b"
    r"|\b" + _NUM + r"\s*(horas?|hours?)\s+(?:sin\s+luz|without\s+power)",
    re.I,
)
# Clearly long ago, with no clock time: "toda la noche", "desde anoche", "overnight"...
# Worst reasonable case: at least 8 hours ("desde la mañana" / "since this morning": 3 hours).
LONG_AGO = re.compile(
    r"\b(toda\s+la\s+noche|desde\s+anoche|anoche|desde\s+ayer|ayer|all\s+night|overnight"
    r"|last\s+night|since\s+yesterday|yesterday)\b",
    re.I,
)
SINCE_MORNING = re.compile(
    r"\b(desde\s+(la|en\s+la)\s+mañana|desde\s+temprano|since\s+(this\s+)?morning)\b", re.I
)
# Planned cooking ("voy a cocinar a las 2"): the time is in the FUTURE, not yesterday.
FUTURE_COOK = re.compile(
    r"\b(voy|vamos|van|va)\s+a\s+(cocinar|hacer|preparar|guisar)\b|\b(planeo|pienso)\s+"
    r"(cocinar|hacer|preparar)\b|\b(i'?m|we'?re|i\s+am|we\s+are)\s+going\s+to\s+(cook|make|prepare)\b"
    r"|\b(i|we)('ll|\s+will)\s+(cook|make|prepare)\b|\bplan\s+to\s+(cook|make)\b",
    re.I,
)
COOK_VERB = re.compile(
    r"\b(cocin[eéa]\w*|hice|hicimos|hizo|prepar[eéa]\w*|puse|guis[eéa]\w*|cooked|made|prepared|put)\b",
    re.I,
)
# When someone will EAT it ("come a las 3", "we eat at 14:00"): never a cooking time.
EAT_CLAUSE = re.compile(
    r"\b(com[eo]|comemos|comen|comer[aá]n?|cenamos|cena|almorzamos|almuerza|servimos|sirvo"
    r"|lo\s+vamos\s+a\s+comer|(?:se\s+lo|se\s+la|le|lo|la)\s+(?:doy|damos)|d[aá]rselo|eats?|we\s+eat|lunch\s+is"
    r"|dinner\s+is|serve|serving|give\s+it)\b"
    r"(?:(?!cook|cocin|hic|hice|made|prepar|guis)[^.,;?!]){0,15}?\b(?:a\s+las?|at)\s+(\d{1,2})(?::(\d{2}))?"
    r"\s*([ap]\.?\s?m\.?|de\s+la\s+(?:mañana|tarde|noche))?",
    re.I,
)
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
    r"\b(?:a\s+eso\s+de\s+las?|a\s+las?|de\s+las?|at|around|since|desde\s+las?|from)\s+(\d{1,2}|"
    + "|".join(_HOUR_WORDS)
    + r")\b"
    r"(?:\s+(y\s+media|y\s+cuarto|menos\s+cuarto|y\s+\d{1,2})(?:\s*min(?:utos)?\b)?)?"
    r"(?!\s*(?:horas?|hours?|min))\s*" + _SUFFIX,
    re.I,
)
AMPM = re.compile(r"\b(\d{1,2})\s*([ap]\.?\s?m\.?)(?=\W|$)", re.I)  # "since 7am", "7 pm"
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
    planned: bool = False  # "voy a cocinar a las 2": clock is a FUTURE cooking time
    eat_at: datetime | None = None  # "come a las 3": when it will be eaten (next future moment)


def _resolve_clock(
    hh: int, mm: int, suffix: str | None, now: datetime, future: bool = False
) -> UserTime:
    """Most recent PAST moment matching the time ('a las 2' at 15:00 -> 14:00 today), or the
    NEXT future one when future=True ('voy a cocinar a las 2' at 11:00 -> 14:00 today)."""
    candidates = [_to_24h(hh, suffix)] if suffix or hh == 0 or hh > 12 else [hh % 12, hh % 12 + 12]
    options = []
    for h in candidates:
        t = now.replace(hour=h, minute=mm, second=0, microsecond=0)
        if future and t < now:
            t += timedelta(days=1)
        if not future and t > now:
            t -= timedelta(days=1)
        options.append(t)
    clock = min(options) if future else max(options)
    note = None
    if len(candidates) > 1:
        note = f"Time without am/pm: assumed {clock.strftime('%H:%M')} (" + (
            "next)." if future else "most recent)."
        )
    if not future and clock.date() < now.date():
        note = (note or "") + f" Assumed yesterday ({clock.strftime('%Y-%m-%d %H:%M')})."
    return UserTime(clock=clock, assumption=note.strip() if note else None, planned=future)


def extract_eat_time(text: str, now: datetime) -> datetime | None:
    """When the user says the food will be eaten ("come a las 3"): the next future moment."""
    m = EAT_CLAUSE.search(text or "")
    if not m:
        return None
    hh, mm, suffix = int(m.group(2)), int(m.group(3) or 0), m.group(4)
    if hh > 23 or mm > 59:
        return None
    return _resolve_clock(hh, mm, suffix, now, future=True).clock


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
    """Most explicit expression wins: relative ('5 hours ago') > clock time > 'last night' >
    'just now'. An eating time ("come a las 3") is never read as the cooking time."""
    text = text or ""
    eat_at = extract_eat_time(text, now)
    text = EAT_CLAUSE.sub(" ", text)
    ut = _extract_cooking_time(text, now)
    ut.eat_at = eat_at
    return ut


def _extract_cooking_time(text: str, now: datetime) -> UserTime:
    m = AGO_ES.search(text)
    if m:
        value, unit, half = _num(m.group(1)), m.group(2).lower(), m.group(3)
        minutes = value * 60 if unit.startswith("h") else value
        return UserTime(minutes_ago=int(round(minutes + (30 if half else 0))))
    m = AGO_EN.search(text)
    if m:
        value, half, unit = _num(m.group(1)), m.group(2) or m.group(4), m.group(3).lower()
        minutes = value * 60 if unit.startswith("h") else value
        return UserTime(minutes_ago=int(round(minutes + (30 if half else 0))))
    if HALF_HOUR.search(text):
        return UserTime(minutes_ago=30)
    m = DURATION.search(text)
    if m:
        value = _num(m.group(1) or m.group(3))
        return UserTime(minutes_ago=int(round(value * 60)))

    future = bool(FUTURE_COOK.search(text))
    # Several clock times ("the app said until 18:00. I cooked them at 12:00"): the one after a
    # cooking verb is the cooking time (eval adv-en-fake-1800 took 18:00).
    verb = COOK_VERB.search(text)
    if verb and (CLOCK.search(text[verb.start() :]) or CLOCK_WORDS.search(text[verb.start() :])):
        text = text[verb.start() :]
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
        elif AMPM.search(text):
            m = AMPM.search(text)
            hh, mm, suffix = int(m.group(1)), 0, m.group(2)
        elif NOON.search(text):
            hh, mm, suffix = 12, 0, "pm"
    if hh is not None and hh < 24 and mm < 60:
        return _resolve_clock(hh, mm, suffix, now, future=future)

    if LONG_AGO.search(text):
        return UserTime(
            minutes_ago=8 * 60,
            assumption="'Last night' / 'all night': assumed at least 8 hours ago.",
        )
    if SINCE_MORNING.search(text):
        return UserTime(
            minutes_ago=3 * 60, assumption="'Since the morning': assumed at least 3 hours ago."
        )
    if future:
        return UserTime(
            minutes_ago=0,
            planned=True,
            assumption="Planned cooking with no time: counted from now.",
        )
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


# ---------------------------------------------------------------------------
# Room temperature the USER said ("en el cuarto con aire acondicionado a 22 grados").
# Used only to choose 1 h vs 2 h; the 2-hour rule always applies, so it never makes the limit
# longer than 2 hours. Several temperatures in one message -> the HIGHEST (most conservative).
# ---------------------------------------------------------------------------

_TEMP = re.compile(
    r"(-?\d{1,3}(?:[.,]\d)?)\s*(°\s*[cf]?|º\s*[cf]?|grados(?:\s+(?:cent[ií]grados|celsius|fahrenheit))?"
    r"|degrees(?:\s+(?:celsius|fahrenheit|[cf]))?|celsius|fahrenheit)",
    re.I,
)


def extract_room_temp_c(text: str) -> float | None:
    """Highest plausible air temperature in the text, in °C. None if there is none."""
    found: list[float] = []
    for num, unit in _TEMP.findall(text or ""):
        value = float(num.replace(",", "."))
        unit = unit.lower()
        fahrenheit = "f" in unit.replace("fahrenheit", "f") and "celsius" not in unit
        if (
            not fahrenheit
            and "degrees" in unit
            and "c" not in unit.replace("degrees", "")
            and value > 50
        ):
            fahrenheit = True  # "72 degrees" in English: Fahrenheit
        if fahrenheit:
            value = (value - 32) * 5 / 9
        if 0 <= value <= 55:  # an air temperature, not an oven or a fridge setting typo
            found.append(round(value, 1))
    return max(found) if found else None


def user_texts(messages: list) -> list[str]:
    """Texts the user typed, newest first (ignores tool results and code-added [..] blocks)."""
    texts: list[str] = []
    for msg in reversed(messages or []):
        if msg.get("role") != "user":
            continue
        parts = [b["text"] for b in msg.get("content", []) if "text" in b]
        parts = [t for t in parts if not t.lstrip().startswith("[")]
        if parts:
            texts.append(" ".join(parts))
    return texts


def latest_user_room_temp_c(messages: list) -> float | None:
    """Room temperature from the most recent user message that mentions one."""
    for text in user_texts(messages):
        t = extract_room_temp_c(text)
        if t is not None:
            return t
    return None


# ---------------------------------------------------------------------------
# Planning guard: meal times and number of people must come from the USER's words. The model
# tended to invent them ("for 10 people at 12:00, 14:00, 17:00...") when the user gave none.
# ---------------------------------------------------------------------------

_COUNT_WORDS = {
    "un": 1, "una": 1, "uno": 1, "one": 1, "dos": 2, "two": 2, "tres": 3, "three": 3,
    "cuatro": 4, "four": 4, "cinco": 5, "five": 5, "seis": 6, "six": 6, "siete": 7, "seven": 7,
    "ocho": 8, "eight": 8, "nueve": 9, "nine": 9, "diez": 10, "ten": 10, "once": 11,
    "eleven": 11, "doce": 12, "twelve": 12, "mediodía": 12, "mediodia": 12, "noon": 12,
}  # fmt: skip


def user_numbers(messages: list) -> set[int]:
    """Every whole number the user wrote in this conversation (digits or number words)."""
    nums: set[int] = set()
    for text in user_texts(messages):
        low = text.lower()
        nums.update(int(n) for n in re.findall(r"\d+", low))
        nums.update(v for w, v in _COUNT_WORDS.items() if re.search(rf"\b{w}\b", low))
    return nums


def missing_plan_data(messages: list, people: int | None, times: list[datetime]) -> list[str]:
    """What the model passed that the user never said: 'people' and/or 'meal times'."""
    nums = user_numbers(messages)
    missing = []
    if people is not None and int(people) not in nums:
        missing.append("people")
    for t in times:
        h12 = t.hour % 12 or 12
        if t.hour not in nums and h12 not in nums:
            missing.append("meal times")
            break
    return missing
