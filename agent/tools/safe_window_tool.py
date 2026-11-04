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


def _temp(c: float) -> str:
    return f"{c:.0f}" if float(c).is_integer() else f"{c:.1f}"


def window_reason(r: dict, language: str) -> str:
    """Why this limit, from the deciding rule and the forecast (empty if nothing to add)."""
    rule = (r.get("deciding_source") or {}).get("rule_id")
    t, th = r.get("max_temp_c"), _temp(r.get("hot_threshold_c") or 32)
    es = language == "es"
    if rule == "FDA_HOT_1H":
        if t is None:
            return (f"Sin pronóstico del clima, suponemos calor (más de {th} °C): límite de 1 hora."
                    if es else f"Without a weather forecast we assume heat (over {th} °C): 1-hour limit.")  # fmt: skip
        return (f"Con más de {th} °C (el pronóstico llega a {_temp(t)} °C), el límite baja de 2 horas a 1."
                if es else f"Above {th} °C (the forecast reaches {_temp(t)} °C), the limit drops from 2 hours to 1.")  # fmt: skip
    if rule in ("WHO_COOKED_2H", "FDA_2H") and t is not None:
        return (f"El pronóstico no pasa de {th} °C (máximo {_temp(t)} °C), así que el límite es de 2 horas."
                if es else f"The forecast stays at or below {th} °C (max {_temp(t)} °C), so the limit is 2 hours.")  # fmt: skip
    if rule == "NHS_RICE_1H":
        return ("El arroz cocido tiene un límite más corto: 1 hora."
                if es else "Cooked rice has a shorter limit: 1 hour.")  # fmt: skip
    return ""


def window_summary(r: dict, language: str) -> str:
    """The key sentence, built in code: the model relays it instead of composing times itself."""
    src_info = r["deciding_source"]
    if src_info.get("kind") == "policy":
        src = (
            "nuestra regla más estricta para bebés y niños pequeños"
            if language == "es"
            else "our stricter rule for babies and young children"
        )
    else:
        src = src_info["source_name"].split(" - ")[0]
    eat_by, remind = r["eat_by_hhmm"], r["reminder_at"][11:16]
    why = window_reason(r, language)
    why = f" {why}" if why else ""
    if language == "es":
        if r["status"] == "discard_now":
            return f"Según {src}, ya pasó el límite: deséchalo ahora.{why}"
        text = f"Según {src}, cómelo antes de las {eat_by} o deséchalo.{why} Puedo recordártelo a las {remind}."
        return text + (
            " Sírvelo de inmediato y no guardes sobras." if r["serve_immediately"] else ""
        )
    if r["status"] == "discard_now":
        return f"According to {src}, the time limit has passed: throw it away now.{why}"
    text = f"According to {src}, eat it before {eat_by} or throw it away.{why} I can remind you at {remind}."
    return text + (" Serve it right away and keep no leftovers." if r["serve_immediately"] else "")


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
    result["summary"] = window_summary(result, tool_context.agent.state.get("language") or "en")
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
