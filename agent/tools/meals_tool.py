from strands import tool

from agent.forecast import get_hourly_temps
from agent.rules_engine import plan_meals as engine_plan_meals
from agent.tools._common import out, parse_local


@tool
def plan_meals(
    people: int,
    meal_times: list[str],
    dishes: list[str],
    audience: str = "general",
    cook_minutes: int = 60,
    lat: float | None = None,
    lon: float | None = None,
) -> str:
    """Household plan: when to cook and how much, so no food sits out too long.

    Args:
        people: How many people eat.
        meal_times: Meal times as 'HH:MM'.
        dishes: Dish names.
        audience: general, infant or young_child.
        cook_minutes: Approximate cooking time per meal.
        lat: Latitude, if known.
        lon: Longitude, if known.
    """
    times = [t for t in (parse_local(m) for m in meal_times) if t is not None]
    if not times:
        return out({"error": "No valid meal times; ask the user (HH:MM)."})
    temps, source = get_hourly_temps(lat, lon)
    result = engine_plan_meals(people, times, dishes, temps, cook_minutes, audience)
    result["forecast_source"] = source
    return out(result)
