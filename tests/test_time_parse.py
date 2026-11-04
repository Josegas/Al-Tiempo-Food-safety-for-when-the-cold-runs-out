from datetime import datetime

import pytest

from agent.time_parse import extract_user_time, last_user_text

NOW = datetime(2026, 11, 4, 12, 0)


@pytest.mark.parametrize(
    ("text", "hhmm"),
    [
        ("cociné frijoles a las 12:00", "12:00"),
        ("cocine frijoles a las 11:30", "11:30"),
        ("I cooked rice at 10:15 am", "10:15"),
        ("a las 9 de la mañana", "09:00"),
        ("at 11 am", "11:00"),
        ("se fue la luz a las 06:00", "06:00"),
        ("a las 2", "02:00"),  # at 12:00, 14:00 is future -> 02:00 today
    ],
)
def test_clock_times(text, hhmm):
    t = extract_user_time(text, NOW)
    assert t.clock is not None and t.clock.strftime("%H:%M") == hhmm


def test_no_ampm_picks_most_recent_past():
    t = extract_user_time("cociné a las 2", datetime(2026, 11, 4, 15, 0))
    assert t.clock == datetime(2026, 11, 4, 14, 0)
    assert "am/pm" in t.assumption


def test_future_time_means_yesterday():
    t = extract_user_time("cooked at 23:00", NOW)
    assert t.clock == datetime(2026, 11, 3, 23, 0)


@pytest.mark.parametrize(
    ("text", "minutes"),
    [
        ("el arroz de hace 5 horas", 300),
        ("rice I cooked 5 hours ago", 300),
        ("hace dos horas", 120),
        ("an hour ago", 60),
        ("hace 45 minutos", 45),
        ("hace media hora", 30),
        ("hace 1.5 horas", 90),
        ("lo acabo de cocinar", 0),
    ],
)
def test_relative_times(text, minutes):
    assert extract_user_time(text, NOW).minutes_ago == minutes


def test_nothing_found():
    t = extract_user_time("cociné frijoles", NOW)
    assert t.clock is None and t.minutes_ago is None


def test_durations_are_not_clock_times():
    assert extract_user_time("¿cuánto dura a las 2 horas?", NOW).clock is None


def test_last_user_text_skips_tool_results():
    msgs = [
        {"role": "user", "content": [{"text": "cociné a las 12:00"}]},
        {"role": "assistant", "content": [{"toolUse": {}}]},
        {"role": "user", "content": [{"toolResult": {}}]},
    ]
    assert last_user_text(msgs) == "cociné a las 12:00"


NOON_DAY = datetime(2026, 11, 4, 22, 0)


@pytest.mark.parametrize(
    "text,expected",
    [
        # Real message from the user's test (live demo, 2026-11-04): it was read as 03:00.
        ("fue un bistek con carne y frijoles guisados en manteca cocine tipo a las 3 y media de la tarde", "15:30"),
        ("a las 3:30 de la tarde", "15:30"),
        ("a las tres y cuarto de la tarde", "15:15"),
        ("a las 2 menos cuarto de la tarde", "13:45"),
        ("a las 4 y 20 de la tarde", "16:20"),
        ("cociné a las 8 y media de la mañana", "08:30"),
        ("a las 9 de la noche", "21:00"),
        ("en la tarde, a las 5 y media", "17:30"),
        ("lo hice al mediodía", "12:00"),
        ("I cooked it at noon", "12:00"),
        ("at seven in the evening", "19:00"),
    ],
)  # fmt: skip
def test_spoken_clock_times(text, expected):
    ut = extract_user_time(text, NOON_DAY)
    assert ut.clock is not None and ut.clock.strftime("%H:%M") == expected


def test_a_las_dos_horas_is_not_a_clock_time():
    assert extract_user_time("lo dejé a las dos horas", NOON_DAY).clock is None
