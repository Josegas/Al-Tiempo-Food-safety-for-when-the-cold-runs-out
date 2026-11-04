"""Target of the one-time EventBridge Scheduler schedules created by the agent.

Stores the delivered reminder for the web app (polled by session) and, if enabled,
sends an SMS with Amazon SNS. Logs the delivery delay to measure "on time" delivery.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

import boto3

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
SMS_ENABLED = os.getenv("SMS_ENABLED", "false").lower() == "true"
TTL_DAYS = 7


def handler(event: dict, _context) -> dict:
    now = datetime.now(UTC)
    fire = event.get("fire_utc")
    delay_s = None
    if fire:
        delay_s = int(
            (
                now - datetime.strptime(fire, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
            ).total_seconds()
        )
    session_id = event.get("session_id") or "anonymous"
    item = {
        "pk": f"SESSION#{session_id}",
        "sk": f"REM#{now.strftime('%Y%m%dT%H%M%S')}#{event.get('reminder_id', '')}",
        "reminder_id": event.get("reminder_id", ""),
        "message": str(event.get("message", ""))[:160],
        "at_local": event.get("at_local", ""),
        "delivered_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at": int((now + timedelta(days=TTL_DAYS)).timestamp()),
    }
    if delay_s is not None:
        item["delay_s"] = delay_s
    TABLE.put_item(Item=item)

    sms_status = "disabled"
    if event.get("channel") == "sms" and event.get("contact"):
        if SMS_ENABLED:
            boto3.client("sns").publish(PhoneNumber=event["contact"], Message=item["message"])
            sms_status = "sent"
        else:
            sms_status = "skipped_sms_disabled"
    # Never log the phone number or the message text.
    print(json.dumps({"event": "reminder_delivered", "delay_s": delay_s,
                      "channel": event.get("channel"), "sms": sms_status}))  # fmt: skip
    return {"ok": True}
