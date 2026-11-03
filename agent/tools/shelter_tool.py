from strands import tool

from agent.forecast import get_hourly_temps
from agent.rules_engine import plan_shelter_batches as engine_plan_shelter
from agent.tools._common import out, parse_local


@tool
def plan_shelter_batches(
    people: int,
    service_windows: list[list[str]],
    dishes: list[str],
    can_hot_hold: bool,
    cook_minutes: int = 60,
    lat: float | None = None,
    lon: float | None = None,
) -> str:
    """Shelter / community kitchen: staggered cooking batches and discard times.

    Args:
        people: People to feed.
        service_windows: List of [start, end] times, e.g. [["13:00","15:00"]].
        dishes: Dish names.
        can_hot_hold: True if food can be kept above 60 °C during service.
        cook_minutes: Approximate cooking time per batch.
        lat: Latitude, if known.
        lon: Longitude, if known.
    """
    windows = []
    for pair in service_windows:
        if len(pair) != 2:
            continue
        start, end = parse_local(pair[0]), parse_local(pair[1])
        if start and end:
            windows.append((start, end))
    if not windows:
        return out({"error": "No valid service windows; ask for start and end times (HH:MM)."})
    temps, source = get_hourly_temps(lat, lon)
    try:
        result = engine_plan_shelter(people, windows, dishes, can_hot_hold, temps, cook_minutes)
    except ValueError as exc:
        return out({"error": str(exc)})
    result["forecast_source"] = source
    return out(result)
