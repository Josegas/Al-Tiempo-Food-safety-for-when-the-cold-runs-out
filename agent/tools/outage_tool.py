from datetime import timedelta

from strands import ToolContext, tool

from agent.rules_engine import track_outage as engine_track_outage
from agent.time_parse import extract_user_time, last_user_text
from agent.tools._common import now_local, out, parse_local


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
    ut = extract_user_time(last_user_text(tool_context.agent.messages), now)
    if ut.minutes_ago is not None:
        started = now - timedelta(minutes=ut.minutes_ago)
    else:
        started = ut.clock or parse_local(outage_started_at)
    if started is None:
        return out({"error": "outage_started_at not understood; ask the user for the time."})
    result = engine_track_outage(started, now, fridge_door_opened, freezer_fullness)
    result["now_hhmm"] = now.strftime("%H:%M")
    return out(result)
