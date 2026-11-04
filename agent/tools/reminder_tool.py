"""schedule_reminder: one-time EventBridge Scheduler schedule that triggers the reminder Lambda.

Without REMINDER_LAMBDA_ARN / SCHEDULER_ROLE_ARN (local dev) it runs as a dry run.
In demo mode the clock is accelerated: the reminder fires ~1 minute from now.
The schedule deletes itself after running (ActionAfterCompletion=DELETE).
"""

import json
import os
import re
import uuid
from datetime import UTC, datetime, timedelta

from strands import ToolContext, tool

from agent.forecast import demo_mode
from agent.tools._common import now_local, out, parse_local, tz

E164 = re.compile(r"^\+[1-9]\d{7,14}$")

# (es noun, es pronoun suffix, en noun)
FOOD_WORDS = {
    "cooked_rice": ("el arroz", "o", "the rice"),
    "infant_formula": ("la fórmula", "a", "the formula"),
}


def reminder_text(window: dict, language: str) -> str:
    """Deterministic reminder text built from the rules-engine result (the LLM never writes times)."""
    es, suffix, en = FOOD_WORDS.get(window["food_type"], ("la comida", "a", "the food"))
    eat_by = window["eat_by_hhmm"]
    src = window["source_name"].split(" - ")[0]  # short publisher name: fits in one SMS
    if language == "es":
        return (
            f"Al Tiempo: come {es} antes de las {eat_by}. Después, deséchal{suffix}. Fuente: {src}"
        )
    return f"Al Tiempo: eat {en} before {eat_by}. After that, throw it away. Source: {src}"


@tool(context=True)
def schedule_reminder(
    at: str,
    message: str,
    tool_context: ToolContext,
    channel: str = "web",
    contact: str | None = None,
) -> str:
    """Schedule a reminder at an exact local time (e.g. the reminder_at time from the rules engine).

    Args:
        at: Local time 'HH:MM' or ISO. Must come from a rules-engine result, never invented.
        message: Short reminder text for the user (max 160 characters).
        channel: 'web' (shown in the app) or 'sms'.
        contact: Phone number in E.164 format (+52...), only for sms.
    """
    state = tool_context.agent.state
    window = state.get("last_window")
    if window:
        if window["status"] == "discard_now":
            return out(
                {
                    "scheduled": False,
                    "error": "food is already past its limit: tell the user to throw it away now",
                }
            )
        at = window["reminder_at_hhmm"]  # code wins over the model's arguments
        message = reminder_text(window, state.get("language") or "en")
    when_local = parse_local(at)
    if when_local is None:
        return out({"scheduled": False, "error": "time not understood"})
    if channel == "sms" and (not contact or not E164.match(contact)):
        return out({"scheduled": False, "error": "sms needs a phone number like +5216671234567"})

    now = now_local()
    if demo_mode():
        fire_utc = datetime.now(UTC) + timedelta(minutes=1)
    else:
        if when_local <= now:
            return out({"scheduled": False, "error": "that time already passed"})
        fire_utc = when_local.replace(tzinfo=tz()).astimezone(UTC)

    reminder_id = uuid.uuid4().hex[:12]
    session_id = state.get("session_id")
    result = {
        "reminder_id": reminder_id,
        "at_local": when_local.strftime("%H:%M"),
        "message": message[:160],
        "channel": channel,
        "demo_accelerated": demo_mode(),
    }
    at_hhmm = result["at_local"]
    result["summary"] = (
        f'Recordatorio programado para las {at_hhmm}: "{result["message"]}"'
        if (state.get("language") or "en") == "es"
        else f'Reminder set for {at_hhmm}: "{result["message"]}"'
    )
    lambda_arn = os.getenv("REMINDER_LAMBDA_ARN")
    role_arn = os.getenv("SCHEDULER_ROLE_ARN")
    if not lambda_arn or not role_arn:
        return out({**result, "scheduled": False, "dry_run": True})

    import boto3

    boto3.client("scheduler").create_schedule(
        Name=f"al-tiempo-{reminder_id}",
        GroupName=os.getenv("SCHEDULE_GROUP", "default"),
        ScheduleExpression=f"at({fire_utc.strftime('%Y-%m-%dT%H:%M:%S')})",
        ScheduleExpressionTimezone="UTC",
        FlexibleTimeWindow={"Mode": "OFF"},
        ActionAfterCompletion="DELETE",
        Target={
            "Arn": lambda_arn,
            "RoleArn": role_arn,
            "Input": json.dumps(
                {
                    "reminder_id": reminder_id,
                    "session_id": session_id,
                    "message": message[:160],
                    "channel": channel,
                    "contact": contact if channel == "sms" else None,
                    "at_local": result["at_local"],
                    "fire_utc": fire_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
            ),
        },
    )
    return out({**result, "scheduled": True})
