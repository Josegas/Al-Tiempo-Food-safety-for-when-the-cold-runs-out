"""schedule_reminder: one-time EventBridge Scheduler schedule that triggers the reminder Lambda.

Without REMINDER_LAMBDA_ARN / SCHEDULER_ROLE_ARN (local dev) it runs as a dry run.
In DEMO_MODE the clock is accelerated: the reminder fires ~1 minute from now.
"""

import json
import os
import uuid
from datetime import UTC, datetime, timedelta

from strands import tool

from agent.forecast import demo_mode
from agent.tools._common import out, parse_local, tz


@tool
def schedule_reminder(
    at: str, message: str, channel: str = "web", contact: str | None = None
) -> str:
    """Schedule a reminder at an exact local time (e.g. the eat-by time from the rules engine).

    Args:
        at: Local time 'HH:MM' or ISO. Must come from a rules-engine result, never invented.
        message: Short reminder text for the user.
        channel: 'web' or 'sms'.
        contact: Phone number in E.164 format, only for sms.
    """
    when_local = parse_local(at)
    if when_local is None:
        return out({"scheduled": False, "error": "time not understood"})
    if demo_mode():
        fire_utc = datetime.now(UTC) + timedelta(minutes=1)
    else:
        fire_utc = when_local.replace(tzinfo=tz()).astimezone(UTC)

    reminder_id = uuid.uuid4().hex[:12]
    lambda_arn = os.getenv("REMINDER_LAMBDA_ARN")
    role_arn = os.getenv("SCHEDULER_ROLE_ARN")
    result = {
        "reminder_id": reminder_id,
        "at_local": when_local.strftime("%H:%M"),
        "channel": channel,
        "demo_accelerated": demo_mode(),
    }
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
                    "message": message,
                    "channel": channel,
                    "contact": contact,
                }
            ),
        },
    )
    return out({**result, "scheduled": True})
