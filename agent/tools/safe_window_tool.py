import re
from datetime import datetime, timedelta

from strands import ToolContext, tool

from agent.forecast import get_hourly_temps
from agent.rules_engine import compute_safe_window as engine_safe_window
from agent.rules_engine import load_rules
from agent.time_parse import (
    extract_user_time,
    last_user_text,
    latest_user_room_temp_c,
    user_texts,
)
from agent.tools._common import now_local, out, parse_local

# Food still on the heat ("siguen en la vaporera echando vapor"): WHO, keep it piping hot
# (> 60 °C) before serving. The room-temperature clock starts when the heat goes off.
HOT_HOLD = re.compile(
    r"vaporera|echando\s+vapor|lumbre\s+prendida|fuego\s+prendido|sigue[n]?\s+(hirviendo|en\s+la\s+lumbre"
    r"|en\s+el\s+fuego|calient)|ba[ñn]o\s+mar[ií]a|still\s+(on\s+the\s+(stove|heat)|steaming|simmering"
    r"|boiling|hot\s+on)|keeping\s+it\s+hot|on\s+low\s+heat|stove\s+(is\s+)?still\s+on",
    re.I,
)
HEAT_OFF = re.compile(
    r"apag|ya\s+no\s+(est[aá]|tiene)\s+(prendid|lumbre|fuego)|turned\s+off|\boff\b", re.I
)


# "no entendí", "what do you mean": the same engine result, said more simply (eval
# mt-es-no-entendi: the model repeated the long summary word for word).
NOT_UNDERSTOOD = re.compile(
    r"no\s+(le\s+|te\s+)?entend|no\s+comprend|expl[ií]came|m[aá]s\s+f[aá]cil|did\s*n'?t\s+understand"
    r"|did\s+not\s+understand|do\s*n'?t\s+understand|do\s+not\s+understand|what\s+do\s+you\s+mean"
    r"|explain\s+(it|that)|simpler",
    re.I,
)


def simple_summary(r: dict, language: str) -> str:
    """One plain sentence with the same engine times, for "I didn't understand"."""
    es = language == "es"
    if r["status"] == "discard_now":
        return ("En pocas palabras: ya no se come; lo más seguro es tirarlo." if es
                else "In short: don't eat it anymore; the safest choice is to throw it away.")  # fmt: skip
    eat_by = r["eat_by_hhmm"]
    return (f"En pocas palabras: cómelo antes de las {eat_by}. Después de esa hora, tíralo." if es
            else f"In short: eat it before {eat_by}. After that time, throw it away.")  # fmt: skip


def is_hot_holding(text: str) -> bool:
    return bool(text) and bool(HOT_HOLD.search(text)) and not HEAT_OFF.search(text)


def resolve_cooked_at(user_text, cooked_at, minutes_ago, now, previous=None, earlier_texts=()):
    """Returns (cooked datetime or None, source, assumption). Only the USER's words count.

    The model's cooked_at / minutes_ago are ignored (kept in the signature for the tool schema):
    when the user gave no time, the model used to invent one ("cooked just now"), and the
    answer looked precise but was made up. With no time, the tool asks for it.
    previous: cooking time the engine used earlier in THIS conversation for the same food. A
    follow-up without a new time ("but the room has air conditioning") keeps it.
    earlier_texts: older user messages; only an absolute clock time is taken from them.
    """
    ut = extract_user_time(user_text, now) if user_text else None
    if ut and ut.minutes_ago is not None:
        return now - timedelta(minutes=ut.minutes_ago), "user_text", ut.assumption
    if ut and ut.clock is not None:
        return ut.clock, "user_text", ut.assumption
    if previous is not None and previous <= now:
        return previous, "user_text", "Same cooking time as earlier in this conversation."
    for text in earlier_texts:
        old = extract_user_time(text, now)
        if old.clock is not None and not old.planned:
            return old.clock, "user_text", "Cooking time from an earlier message."
    return None, "unknown", None


def _temp(c: float) -> str:
    return f"{c:.0f}" if float(c).is_integer() else f"{c:.1f}"


def window_reason(r: dict, language: str) -> str:
    """Why this limit, in ONE plain sentence: the deciding rule's "why" (rules/*.yaml, backed by
    its source) plus the forecast data that chose it. Empty if the rule has no "why"."""
    from agent.rules_engine import load_rules

    rule_id = (r.get("deciding_source") or {}).get("rule_id")
    rule = load_rules().get(rule_id)
    why = rule.why_in(language).rstrip(".") if rule else ""
    if not why:
        return ""
    t, th = r.get("max_temp_c"), _temp(r.get("hot_threshold_c") or 32)
    es = language == "es"
    if r.get("temp_source") == "user" and t is not None:
        if rule_id == "FDA_HOT_1H":
            detail = (f"con la temperatura que me dijiste ({_temp(t)} °C), que pasa de {th} °C, el límite es de 1 hora"
                      if es else f"with the temperature you told me ({_temp(t)} °C), above {th} °C, the limit is 1 hour")  # fmt: skip
            return f"{why}: {detail}."
        if rule_id in ("WHO_COOKED_2H", "FDA_2H"):
            detail = (f"con la temperatura que me dijiste ({_temp(t)} °C) el límite es de 2 horas, no de 1; "
                      "a temperatura ambiente nunca es más de 2 horas, aunque el cuarto esté fresco"
                      if es else f"with the temperature you told me ({_temp(t)} °C) the limit is 2 hours, not 1; "
                      "at room temperature it is never more than 2 hours, even in a cool room")  # fmt: skip
            return f"{why}: {detail}."
    if rule_id == "FDA_HOT_1H":
        if t is None:
            detail = (f"sin pronóstico del clima suponemos más de {th} °C, así que el límite es de 1 hora"
                      if es else f"without a weather forecast we assume over {th} °C, so the limit is 1 hour")  # fmt: skip
        else:
            detail = (f"con más de {th} °C (el pronóstico llega a {_temp(t)} °C), el límite baja de 2 horas a 1"
                      if es else f"above {th} °C (the forecast reaches {_temp(t)} °C), the limit drops from 2 hours to 1")  # fmt: skip
        return f"{why}: {detail}."
    if rule_id in ("WHO_COOKED_2H", "FDA_2H") and t is not None:
        detail = (f"el pronóstico no pasa de {th} °C (máximo {_temp(t)} °C), así que el límite es de 2 horas"
                  if es else f"the forecast stays at or below {th} °C (max {_temp(t)} °C), so the limit is 2 hours")  # fmt: skip
        return f"{why}: {detail}."
    if rule_id in ("NHS_RICE_1H", "POLICY_CHILD_STRICT"):
        return f"{why}; " + (
            "por eso el límite es de 1 hora." if es else "that is why the limit is 1 hour."
        )
    return f"{why}."


def heat_curve(temps, start: datetime, end: datetime) -> list[list] | None:
    """Hourly forecast from 2 hours before `start` to 3 hours after `end` (at most 14 points),
    as [["HH:MM", °C], ...]. Only for drawing; no decision uses it."""
    if not temps:
        return None
    lo = start.replace(minute=0, second=0, microsecond=0) - timedelta(hours=2)
    hi = end + timedelta(hours=3)
    pts = [[ts.strftime("%H:%M"), round(float(t), 1)] for ts, t in temps if lo <= ts <= hi]
    return pts[:14] if len(pts) >= 3 else None


def short_reason(r: dict, language: str) -> str:
    """The reason in a few words, for the answer people read. The long version with forecast
    numbers (window_reason) stays in the result's "why", the timeline and "Look inside"."""
    es = language == "es"
    rule_id = (r.get("deciding_source") or {}).get("rule_id")
    t, user = r.get("max_temp_c"), r.get("temp_source") == "user"
    if rule_id == "FDA_HOT_1H":
        if user and t is not None:
            return (f"Con los {_temp(t)} °C que me dijiste las bacterias crecen rápido: aguanta 1 hora." if es
                    else f"At the {_temp(t)} °C you told me, bacteria grow fast: it lasts 1 hour.")  # fmt: skip
        if t is None:
            return ("Sin pronóstico suponemos calor, y con calor las bacterias crecen más rápido: aguanta 1 hora." if es
                    else "With no forecast we assume heat, and in heat bacteria grow faster: it lasts 1 hour.")  # fmt: skip
        return ("Con este calor (más de 32 °C) las bacterias crecen más rápido: aguanta 1 hora, no 2." if es
                else "In this heat (over 32 °C) bacteria grow faster: it lasts 1 hour, not 2.")  # fmt: skip
    if rule_id in ("WHO_COOKED_2H", "FDA_2H"):
        if user and t is not None:
            return (f"Con los {_temp(t)} °C que me dijiste aguanta 2 horas, nunca más: afuera del refri las bacterias se multiplican." if es
                    else f"At the {_temp(t)} °C you told me, it lasts 2 hours, never more: out of the fridge bacteria multiply.")  # fmt: skip
        return ("Afuera del refri las bacterias se multiplican: aguanta 2 horas, nunca más." if es
                else "Out of the fridge bacteria multiply: it lasts 2 hours, never more.")  # fmt: skip
    if rule_id == "NHS_RICE_1H":
        return ("El arroz cocido aguanta 1 hora: forma toxinas que recalentar no quita." if es
                else "Cooked rice lasts 1 hour: it forms toxins that reheating does not remove.")  # fmt: skip
    if rule_id == "POLICY_CHILD_STRICT":
        return ("Los niños pequeños se enferman más con comida contaminada: para ellos usamos 1 hora." if es
                else "Young children get sick more from unsafe food: for them we use 1 hour.")  # fmt: skip
    rule = load_rules().get(rule_id) if rule_id else None
    why = rule.why_in(language).rstrip(".") if rule else ""
    return f"{why}." if why else ""


def _source(r: dict, language: str) -> str:
    src_info = r["deciding_source"]
    if src_info.get("kind") == "policy":
        return ("nuestra regla para bebés y niños pequeños" if language == "es"
                else "our rule for babies and young children")  # fmt: skip
    return src_info["source_name"].split(" - ")[0]


def window_summary(r: dict, language: str) -> str:
    """The key sentences, built in code and SHORT: decision, a few-word reason, next step.
    The model relays them instead of composing times itself."""
    src = _source(r, language)
    eat_by, remind = r["eat_by_hhmm"], r["reminder_at"][11:16]
    why = short_reason(r, language)
    why = f" {why}" if why else ""
    special = _special_summary(r, language, src, eat_by, remind, why)
    if special:
        return special
    es = language == "es"
    kids = r["serve_immediately"]
    if r["status"] == "discard_now":
        if es:
            return (f"Según {src}, ya pasó el límite: lo más seguro es no comerlo y tirarlo.{why} "
                    "Sé que da lástima; la próxima vez dime la hora y te aviso antes.")  # fmt: skip
        return (f"According to {src}, the limit has passed: the safest choice is not to eat it and "
                f"to throw it away.{why} I know it's a pity; next time tell me the time and I'll "
                "remind you before.")  # fmt: skip
    if es:
        extra = " Sírvelo ya y no guardes sobras." if kids else f" ¿Te aviso a las {remind}?"
        return f"Según {src}, cómelo antes de las {eat_by} o deséchalo.{why}{extra}"
    extra = " Serve it now and keep no leftovers." if kids else f" Shall I remind you at {remind}?"
    return f"According to {src}, eat it before {eat_by} or throw it away.{why}{extra}"


def _special_summary(r: dict, language: str, src: str, eat_by: str, remind: str, why: str) -> str:
    """Unknown time (ask), still on the heat, planned cooking, or "won't last until mealtime"."""
    es = language == "es"
    hours = r["limit_minutes"] // 60
    unit = ("hora" if hours == 1 else "horas") if es else ("hour" if hours == 1 else "hours")
    if r.get("time_source") == "unknown":
        if r.get("serve_immediately"):
            return ("¿A qué hora lo cocinaste? Para bebés y niños pequeños no se guardan sobras: lo más "
                    "seguro es tirarlas." if es else "When did you cook it? For babies and young children "
                    "keep no leftovers: the safest choice is to throw them away.")  # fmt: skip
        reason = why.strip() or (f"Aguanta {hours} {unit}." if es else f"It lasts {hours} {unit}.")
        reason = reason[:1].lower() + reason[1:]
        return (f"¿A qué hora lo cocinaste? Según {src}: {reason} Si pasó más tiempo o no lo sabes, "
                "lo más seguro es tirarlo." if es else
                f"When did you cook it? According to {src}: {reason} If more time has passed or you "
                "don't know, the safest choice is to throw it away.")  # fmt: skip
    if r.get("hot_holding"):
        return (f"Mientras siga echando vapor (más de 60 °C) los microbios casi no crecen, así que el "
                f"tiempo no corre. Si apagas el fuego "
                f"ahora, según {src}, cómelo antes de las {eat_by}." if es else
                f"While it keeps steaming (above 60 °C) germs barely grow, so the clock does not run. "
                f"If you turn off the "
                f"heat now, according to {src}, eat it before {eat_by}.")  # fmt: skip
    if r.get("planned"):
        cooked = r["cooked_at_hhmm"]
        return (f"Si lo cocinas a las {cooked}, según {src}, cómelo antes de las {eat_by}.{why} Cocina "
                f"solo lo que se va a comer. ¿Te aviso a las {remind}?" if es else
                f"If you cook it at {cooked}, according to {src}, eat it before {eat_by}.{why} Cook only "
                f"what will be eaten. Shall I remind you at {remind}?")  # fmt: skip
    if r.get("wont_last_until") and r["status"] != "discard_now":
        eat_at = r["wont_last_until"]
        return (f"No aguanta hasta las {eat_at}: según {src}, cómelo antes de las {eat_by} o "
                f"deséchalo.{why} Mejor prepáralo más cerca de la hora de comer." if es else
                f"It won't last until {eat_at}: according to {src}, eat it before {eat_by} or throw it "
                f"away.{why} Better to make it closer to mealtime.")  # fmt: skip
    return ""


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
    messages = tool_context.agent.messages
    user_text = last_user_text(messages)
    hot_holding = is_hot_holding(user_text)
    ut = extract_user_time(user_text, now) if user_text else None
    last = tool_context.agent.state.get("last_window") or {}
    previous = None
    if last.get("food_type") == food_type and last.get("time_source") == "user_text":
        try:
            previous = datetime.fromisoformat(last.get("cooked_at") or "")
        except ValueError:
            previous = None
    cooked, time_source, note = resolve_cooked_at(
        user_text, cooked_at, minutes_ago, now, previous, user_texts(messages)[1:]
    )
    planned = bool(ut and ut.planned and cooked is not None and cooked >= now)
    if hot_holding:
        cooked, time_source = now, "user_text"
        note = (
            "Still on the heat (hot holding, WHO > 60 °C): the room-temperature clock starts "
            "when the heat goes off; counted from now."
        )
    if cooked is None:
        # Unknown cooking time: worst case = it may already be past the limit.
        cooked = now - timedelta(hours=24)
        note = "Cooking time unknown: assumed it was cooked long ago, so it should be discarded. Ask the user for the time."
    temps, source = get_hourly_temps(lat, lon)
    room_temp = latest_user_room_temp_c(messages)  # the user's words, never the model's
    result = engine_safe_window(
        food_type,
        cooked,
        audience,
        temps,
        parse_local(feeding_started_at),
        now=now,
        room_temp_c=room_temp,
    ).to_dict()
    if note:
        result["assumptions"].append(note)
    result["planned"] = planned
    result["hot_holding"] = hot_holding
    if hot_holding:
        from agent.rules_engine import get_rule

        hold = get_rule("WHO_HOT_HOLD_60C")
        result["rule_ids"].insert(0, hold.id)
        result["sources"].insert(0, hold.source())
    eat_at = ut.eat_at if ut else None
    eat_by_dt = datetime.fromisoformat(result["eat_by"])
    if eat_at is not None and eat_at > eat_by_dt:
        result["wont_last_until"] = eat_at.strftime("%H:%M")
    result["cooked_at_hhmm"] = cooked.strftime("%H:%M")
    result["time_source"] = time_source
    result["now_hhmm"] = now.strftime("%H:%M")
    result["forecast_source"] = source
    lang = tool_context.agent.state.get("language") or "en"
    result["why"] = window_reason(result, lang)  # the rule's reason, in one sentence (rules/*.yaml)
    result["summary"] = window_summary(result, lang)
    if time_source != "unknown" and NOT_UNDERSTOOD.search(user_text or ""):
        result["summary"] = simple_summary(result, lang)
    # The day's heat curve for the web (hours around the window). Kept in agent STATE, never in the
    # tool result: the model doesn't see it, so the verifier's list of allowed times stays small.
    tool_context.agent.state.set(
        "last_hourly",
        heat_curve(temps, cooked, eat_by_dt) if result["temp_source"] == "forecast" else None,
    )
    # Remembered for schedule_reminder: the reminder's time and text come from here, not the model.
    tool_context.agent.state.set(
        "last_window",
        {
            "food_type": food_type,
            "eat_by_hhmm": result["eat_by_hhmm"],
            "eat_by": result["eat_by"],
            "cooked_at_hhmm": result["cooked_at_hhmm"],
            "cooked_at": cooked.isoformat(),
            "time_source": time_source,
            "reminder_at_hhmm": result["reminder_at"][11:16],
            "status": result["status"],
            "source_name": result["deciding_source"]["source_name"],
            "rule_ids": result["rule_ids"],
        },
    )
    return out(result)
