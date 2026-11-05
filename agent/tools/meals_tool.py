from strands import ToolContext, tool

from agent.forecast import get_hourly_temps
from agent.rules_engine import plan_meals as engine_plan_meals
from agent.time_parse import missing_plan_data, user_numbers
from agent.tools._common import out, parse_local

# Raw dishes are prepared, not cooked: no cooking lead time (the model kept saying "cook the
# salad at 13:00"). Decided in code from the dish names.
RAW_WORDS = ("ensalada", "salad", "lechuga", "lettuce", "fruta", "fruit", "pico de gallo")


def is_raw(dishes: list[str]) -> bool:
    low = " ".join(dishes or []).lower()
    return bool(low) and any(w in low for w in RAW_WORDS)


@tool(context=True)
def plan_meals(
    people: int,
    meal_times: list[str],
    dishes: list[str],
    tool_context: ToolContext,
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
    missing = missing_plan_data(tool_context.agent.messages, people, times)
    if missing:
        return out(
            {
                "error": "not_said_by_user",
                "missing": missing,
                "user_said_numbers": sorted(user_numbers(tool_context.agent.messages)),
                "instruction": "Do not invent people or times. Call the tool again using only "
                "numbers the user wrote (user_said_numbers); for one meal time with no end time, "
                "use plan_meals. If something is really missing, ask the user for it.",
            }
        )
    raw = is_raw(dishes)
    if raw:
        cook_minutes = 0
    temps, source = get_hourly_temps(lat, lon)
    result = engine_plan_meals(people, times, dishes, temps, cook_minutes, audience)
    result["forecast_source"] = source
    if raw:
        result["raw_food"] = True
        result["advice"] = (
            "Raw food: say 'prepare it right before serving' (never 'cook it'). "
            "Prepare only what will be eaten at this meal; do not keep leftovers at room temperature."
        )
    return out(result)
