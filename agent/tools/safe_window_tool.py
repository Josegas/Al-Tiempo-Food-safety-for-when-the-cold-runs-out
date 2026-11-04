from datetime import timedelta

from strands import ToolContext, tool

from agent.forecast import get_hourly_temps
from agent.rules_engine import compute_safe_window as engine_safe_window
from agent.time_parse import extract_user_time, last_user_text
from agent.tools._common import now_local, out, parse_local


def resolve_cooked_at(user_text, cooked_at, minutes_ago, now):
    """Returns (cooked datetime or None, source, assumption). User's own words win over the LLM."""
    ut = extract_user_time(user_text, now) if user_text else None
    if ut and ut.minutes_ago is not None:
        return now - timedelta(minutes=ut.minutes_ago), "user_text", None
    if ut and ut.clock is not None:
        return ut.clock, "user_text", ut.assumption
    if minutes_ago is not None:
        return now - timedelta(minutes=max(int(minutes_ago), 0)), "model", None
    cooked = parse_local(cooked_at)
    if cooked is not None:
        if cooked > now:
            cooked -= timedelta(days=1)
        return cooked, "model", None
    return None, "unknown", None


@tool(context=True)
def compute_safe_window(
    food_type: str,
    tool_context: ToolContext,
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
        cooked_at: Clock time when it was cooked, 'HH:MM', exactly as the user said it.
        minutes_ago: If the user says how long ago it was cooked ("5 hours ago" -> 300).
        audience: general, infant, or young_child (under 5). Strict rules for children.
        lat: Latitude of the user, if known.
        lon: Longitude of the user, if known.
        feeding_started_at: For infant formula, when the baby started drinking ('HH:MM').
    """
    now = now_local()
    user_text = last_user_text(tool_context.agent.messages)
    cooked, time_source, note = resolve_cooked_at(user_text, cooked_at, minutes_ago, now)
    if cooked is None:
        # Unknown cooking time: worst case = it may already be past the limit.
        cooked = now - timedelta(hours=24)
        note = "Cooking time unknown: assumed it was cooked long ago, so it should be discarded. Ask the user for the time."
    temps, source = get_hourly_temps(lat, lon)
    result = engine_safe_window(
        food_type, cooked, audience, temps, parse_local(feeding_started_at), now=now
    ).to_dict()
    if note:
        result["assumptions"].append(note)
    result["cooked_at_hhmm"] = cooked.strftime("%H:%M")
    result["time_source"] = time_source
    result["now_hhmm"] = now.strftime("%H:%M")
    result["forecast_source"] = source
    # Remembered for schedule_reminder: the reminder's time and text come from here, not the model.
    tool_context.agent.state.set(
        "last_window",
        {
            "food_type": food_type,
            "eat_by_hhmm": result["eat_by_hhmm"],
            "reminder_at_hhmm": result["reminder_at"][11:16],
            "status": result["status"],
            "source_name": result["deciding_source"]["source_name"],
        },
    )
    return out(result)
