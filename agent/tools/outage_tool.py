from strands import tool

from agent.rules_engine import track_outage as engine_track_outage
from agent.tools._common import now_local, out, parse_local


@tool
def track_outage(
    outage_started_at: str,
    fridge_door_opened: bool | None = None,
    freezer_fullness: str | None = None,
) -> str:
    """Power-outage mode: how long the fridge and freezer keep food safe (official rules).

    Args:
        outage_started_at: When the power went out, 'HH:MM' or ISO.
        fridge_door_opened: True if the fridge was opened since the outage, None if unknown.
        freezer_fullness: 'full', 'half', or empty if unknown.
    """
    started = parse_local(outage_started_at)
    if started is None:
        return out({"error": "outage_started_at not understood; ask the user for the time."})
    now = now_local()
    result = engine_track_outage(started, now, fridge_door_opened, freezer_fullness)
    result["now_hhmm"] = now.strftime("%H:%M")
    return out(result)
