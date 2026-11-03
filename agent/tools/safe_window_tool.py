from datetime import timedelta

from strands import tool

from agent.forecast import get_hourly_temps
from agent.rules_engine import compute_safe_window as engine_safe_window
from agent.tools._common import now_local, out, parse_local


@tool
def compute_safe_window(
    food_type: str,
    cooked_at: str | None = None,
    minutes_ago: int | None = None,
    audience: str = "general",
    lat: float | None = None,
    lon: float | None = None,
    feeding_started_at: str | None = None,
) -> str:
    """Latest time to eat food kept at room temperature (no fridge), from official rules.

    Args:
        food_type: One of cooked_food, cooked_rice, infant_formula. Use cooked_food if unsure.
        cooked_at: Clock time when it was cooked/prepared, 'HH:MM' or ISO.
        minutes_ago: Use this instead of cooked_at when the user says how long ago it was
            cooked (e.g. "5 hours ago" -> 300). If neither is given, the rule assumes it was
            cooked long ago (unknown = discard).
        audience: general, infant, or young_child (under 5). Strict rules for children.
        lat: Latitude of the user, if known.
        lon: Longitude of the user, if known.
        feeding_started_at: For infant formula, when the baby started drinking ('HH:MM').
    """
    now = now_local()
    note = None
    if minutes_ago is not None:
        cooked = now - timedelta(minutes=max(int(minutes_ago), 0))
    else:
        cooked = parse_local(cooked_at)
        if cooked is not None and cooked > now:
            cooked -= timedelta(days=1)  # "cooked at 23:00" asked after midnight
    if cooked is None:
        # Unknown cooking time: worst case = it may already be past the limit.
        cooked = now - timedelta(hours=24)
        note = "Cooking time unknown: assumed it was cooked long ago, so it should be discarded."
    temps, source = get_hourly_temps(lat, lon)
    result = engine_safe_window(
        food_type, cooked, audience, temps, parse_local(feeding_started_at), now=now
    ).to_dict()
    if note:
        result["assumptions"].append(note)
    result["now_hhmm"] = now.strftime("%H:%M")
    result["forecast_source"] = source
    return out(result)
