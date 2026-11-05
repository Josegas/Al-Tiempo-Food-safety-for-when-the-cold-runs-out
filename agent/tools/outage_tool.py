import re
from datetime import timedelta

from strands import ToolContext, tool

from agent.rules_engine import track_outage as engine_track_outage
from agent.time_parse import extract_user_time, last_user_text
from agent.tools._common import now_local, out, parse_local

# The user's own words win over the model's arguments (same idea as times: the model sometimes
# drops "I kept the fridge closed", which made the engine assume the worst case).
DOOR_CLOSED = re.compile(
    r"(kept|keep|stayed|remained|is|was)\s+(the\s+)?(fridge|refrigerator)?(\s+door)?\s*closed"
    r"|(have|has|had|did)\s*(n'?t|\s+not)\s+(been\s+)?open"
    r"|haven'?t\s+opened|didn'?t\s+open|not\s+opened"
    r"|no\s+(lo\s+|la\s+)?(he|hemos|han|ha)\s+abiert|no\s+(lo\s+|la\s+)?(abr[ií]|abrimos|abrieron)"
    r"|(refri|refrigerador|nevera)\w*\s+((sigue|est[aá]|qued[oó])\s+)?(cerrad|sin\s+abrir)"
    r"|mantuv\w+\s+.*cerrad",
    re.I,
)
DOOR_OPENED = re.compile(
    r"\b(i|we|they|someone)\s+(opened|open)\b|\b(abr[ií]|abrimos|abrieron|he\s+abierto|hemos\s+abierto)\b",
    re.I,
)
FREEZER_FULL = re.compile(
    r"(freezer|congelador)\w*[^.]{0,25}\b(full|llen[oa])\b|\bfull\s+freezer\b", re.I
)
FREEZER_HALF = re.compile(
    r"(freezer|congelador)\w*[^.]{0,25}(half|a\s+medias|medio|mitad)|half[- ]full\s+freezer", re.I
)


# "the ice cubes melted and froze again", "se derritió el hielo", "se descongeló"
FREEZER_THAWED = re.compile(
    r"melted|thawed|defrost|refroze|froze\s+again|derriti|descongel|deshiel|volvi\w+\s+a\s+congelar",
    re.I,
)


MENTIONS_FREEZER = re.compile(r"freezer|congelad|frozen", re.I)


def _fridge_only(summary: str) -> str:
    """Drops the freezer sentence(s) from the engine summary (they start with Freezer:/Congelador:)."""
    for tag in ("Freezer:", "Congelador:"):
        if tag in summary:
            head, _, rest = summary.partition(tag)
            # the closing "why" sentence after the freezer part is about the fridge: keep it
            tail = rest.split(". ")
            keep = [t for t in tail if t.startswith(("A closed fridge", "El refrigerador cerrado"))]
            return (head.strip() + (" " + ". ".join(keep) if keep else "")).strip()
    return summary


def door_and_freezer_from_text(text: str) -> tuple[bool | None, str | None]:
    door = False if DOOR_CLOSED.search(text) else True if DOOR_OPENED.search(text) else None
    freezer = "half" if FREEZER_HALF.search(text) else "full" if FREEZER_FULL.search(text) else None
    return door, freezer


@tool(context=True)
def track_outage(
    tool_context: ToolContext,
    outage_started_at: str | None = None,
    fridge_door_opened: bool | None = None,
    freezer_fullness: str | None = None,
) -> str:
    """Power-outage mode: how long the fridge and freezer keep food safe (official rules).

    Args:
        outage_started_at: When the power went out, 'HH:MM' or ISO.
        fridge_door_opened: True if the fridge was opened since the outage, None if unknown.
        freezer_fullness: 'full', 'half', or empty if unknown.
    """
    now = now_local()
    text = last_user_text(tool_context.agent.messages)
    door, freezer = door_and_freezer_from_text(text)
    fridge_door_opened = door if door is not None else fridge_door_opened
    freezer_fullness = freezer or freezer_fullness
    ut = extract_user_time(text, now)
    if ut.minutes_ago is not None:
        started = now - timedelta(minutes=ut.minutes_ago)
    else:
        started = ut.clock or parse_local(outage_started_at)
    if started is None:
        return out({"error": "outage_started_at not understood; ask the user for the time."})
    thawed = bool(FREEZER_THAWED.search(text))
    result = engine_track_outage(started, now, fridge_door_opened, freezer_fullness, thawed)
    result["now_hhmm"] = now.strftime("%H:%M")
    if not MENTIONS_FREEZER.search(text):
        # The user only talked about the fridge: the summary says nothing about the freezer, so
        # the model can't move their food there (eval rw-13: "the raw chicken is safe in the
        # freezer until tomorrow", when the user never mentioned a freezer).
        result["summary"] = {lang: _fridge_only(txt) for lang, txt in result["summary"].items()}
        result["freezer_mentioned"] = False
        result["freezer_safe_until"] = result["freezer_safe_until_hhmm"] = None
        result["freezer_status"] = "not_mentioned_by_user"
    tool_context.agent.state.set("last_window", None)  # a later reminder is not about a dish
    return out(result)
