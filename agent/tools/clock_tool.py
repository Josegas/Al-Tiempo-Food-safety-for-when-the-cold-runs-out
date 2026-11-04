from strands import ToolContext, tool

from agent.forecast import demo_mode
from agent.tools._common import now_local, out, tz


@tool(context=True)
def get_current_time(tool_context: ToolContext) -> str:
    """The user's current local date and time. Use it when the user asks what time or day it is.
    In simulated (demo) mode it returns the demo clock, fixed at 12:00."""
    now = now_local()
    simulated = demo_mode()
    hhmm = now.strftime("%H:%M")
    es = (tool_context.agent.state.get("language") or "en") == "es"
    if es:
        summary = f"Son las {hhmm}" + (
            " (reloj de la demo, no la hora real)." if simulated else "."
        )
    else:
        summary = f"It is {hhmm}" + (" (demo clock, not the real time)." if simulated else ".")
    return out(
        {
            "now_hhmm": hhmm,
            "summary": summary,
            "date": now.date().isoformat(),
            "timezone": tz().key,
            "simulated": simulated,
            "note": "Simulated mode: this is the demo clock, fixed at 12:00, not the real time."
            if simulated
            else "",
        }
    )
