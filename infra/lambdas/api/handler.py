"""Public API behind CloudFront (/api/*). Thin layer: validation, daily cap, AgentCore call.

Routes:
  POST /api/chat       {prompt, language, session_id, demo, timezone, lat, lon}
  GET  /api/reminders  ?session_id=...
  POST /api/voice      {text, language}  -> mp3 (base64) from Amazon Polly
  POST /api/warm       {session_id, language, demo} -> starts the AgentCore session (no model call)
  GET  /api/health
  POST /api/comprehension {correct: bool} -> anonymous counters (no session, no text, no IP)
  GET  /api/comprehension                 -> {answered, correct}
No prompt text is logged (privacy): only sizes, latency and outcome.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from datetime import UTC, datetime, timedelta

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import ClientError

TABLE = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
AGENTCORE = boto3.client(
    "bedrock-agentcore",
    config=Config(read_timeout=28, connect_timeout=3, retries={"max_attempts": 1}),
)
POLLY = boto3.client("polly")

RUNTIME_ARN = os.environ["RUNTIME_ARN"]
DAILY_CAP = int(os.getenv("DAILY_CAP", "500"))
WARM_CAP = int(os.getenv("WARM_CAP", "1000"))  # warm-ups start a session: capped separately
SESSION_RE = re.compile(r"^[A-Za-z0-9-]{33,100}$")
VOICES = {"es": "Mia", "en": "Joanna"}  # es-MX / en-US
MAX_VOICE_CHARS = 600
QUIZ_CAP = int(os.getenv("QUIZ_CAP", "2000"))  # comprehension answers per day (anti-spam)
STATS_KEY = {"pk": "STATS", "sk": "comprehension"}  # one aggregate item, nothing personal

MESSAGES = {
    "cap": {
        "en": "The demo reached today's limit of conversations (it protects the project's budget). Please try again tomorrow.",
        "es": "La demo llegó al límite de conversaciones de hoy (así cuidamos el presupuesto del proyecto). Intenta de nuevo mañana.",
    },
    "busy": {
        "en": "Sorry, I could not answer right now. If in doubt, throw the food away.",
        "es": "Perdón, no pude responder ahora. Si tienes duda, tira la comida.",
    },
}


def _resp(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json", "cache-control": "no-store"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _log(**fields) -> None:
    print(json.dumps({"event": "api", **fields}))


def _take_daily_slot(kind: str = "chat", cap: int | None = None) -> bool:
    """Atomic counter in DynamoDB. False when today's cap is reached."""
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    try:
        TABLE.update_item(
            Key={"pk": f"COUNTER#{day}", "sk": kind},
            UpdateExpression="ADD n :one SET expires_at = :ttl",
            ConditionExpression="attribute_not_exists(n) OR n < :cap",
            ExpressionAttributeValues={
                ":one": 1,
                ":cap": DAILY_CAP if cap is None else cap,
                ":ttl": int((datetime.now(UTC) + timedelta(days=3)).timestamp()),
            },
        )
        return True
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def chat(body: dict) -> dict:
    language = body.get("language") if body.get("language") in ("en", "es") else "en"
    prompt = str(body.get("prompt", "")).strip()
    session_id = str(body.get("session_id", ""))
    if not prompt or len(prompt) > 1000:
        return _resp(400, {"error": "prompt must be 1-1000 characters"})
    if not SESSION_RE.match(session_id):
        return _resp(400, {"error": "invalid session_id"})
    if not _take_daily_slot():
        _log(route="chat", outcome="daily_cap")
        return _resp(429, {"answer": MESSAGES["cap"][language], "error": "daily_cap"})

    payload = {
        "prompt": prompt,
        "language": language,
        "demo": body.get("demo") if isinstance(body.get("demo"), bool) else True,
        "timezone": body.get("timezone"),
        "lat": body.get("lat"),
        "lon": body.get("lon"),
    }
    started = time.perf_counter()
    try:
        resp = AGENTCORE.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            contentType="application/json",
            accept="application/json",
            payload=json.dumps(payload).encode("utf-8"),
        )
        result = json.loads(resp["response"].read())
    except Exception as exc:  # timeout, throttling, runtime error -> safe message
        _log(route="chat", outcome="error", error=type(exc).__name__)
        return _resp(502, {"answer": MESSAGES["busy"][language], "error": type(exc).__name__})
    ms = int((time.perf_counter() - started) * 1000)
    metrics = result.get("metrics", {})
    _log(route="chat", outcome="ok", latency_ms=ms, prompt_chars=len(prompt),
         tools=metrics.get("tools_used"), verifier_blocked=metrics.get("verifier_blocked"))  # fmt: skip
    out = {"answer": result.get("answer", ""), "metrics": {**metrics, "api_ms": ms}}
    if isinstance(result.get("decision"), dict):  # engine numbers for the web timeline (optional)
        out["decision"] = result["decision"]
    if isinstance(result.get("hygiene_tip"), dict):  # optional hygiene tip chosen by code
        out["hygiene_tip"] = result["hygiene_tip"]
    return _resp(200, out)


def warm(body: dict) -> dict:
    """Start the user's AgentCore session while they read the page (no model call, no tokens)."""
    language = body.get("language") if body.get("language") in ("en", "es") else "en"
    session_id = str(body.get("session_id", ""))
    if not SESSION_RE.match(session_id):
        return _resp(400, {"error": "invalid session_id"})
    if not _take_daily_slot("warm", WARM_CAP):
        _log(route="warm", outcome="daily_cap")
        return _resp(429, {"warm": False, "error": "daily_cap"})
    payload = {
        "warmup": True,
        "language": language,
        "demo": body.get("demo") if isinstance(body.get("demo"), bool) else True,
    }
    started = time.perf_counter()
    try:
        AGENTCORE.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            contentType="application/json",
            accept="application/json",
            payload=json.dumps(payload).encode("utf-8"),
        )["response"].read()
    except Exception as exc:  # warm-up is best effort: the chat still works without it
        _log(route="warm", outcome="error", error=type(exc).__name__)
        return _resp(502, {"warm": False, "error": type(exc).__name__})
    ms = int((time.perf_counter() - started) * 1000)
    _log(route="warm", outcome="ok", latency_ms=ms)
    return _resp(200, {"warm": True, "ms": ms})


def reminders(params: dict) -> dict:
    session_id = (params or {}).get("session_id", "")
    if not SESSION_RE.match(session_id):
        return _resp(400, {"error": "invalid session_id"})
    items = TABLE.query(
        KeyConditionExpression=Key("pk").eq(f"SESSION#{session_id}")
        & Key("sk").begins_with("REM#"),
        Limit=20,
    )["Items"]
    out = [
        {k: (int(v) if k == "delay_s" else v) for k, v in it.items() if k in
         ("reminder_id", "message", "at_local", "delivered_at", "delay_s")}
        for it in items
    ]  # fmt: skip
    return _resp(200, {"reminders": out})


def voice(body: dict) -> dict:
    language = body.get("language") if body.get("language") in ("en", "es") else "en"
    text = str(body.get("text", "")).strip()[:MAX_VOICE_CHARS]
    if not text:
        return _resp(400, {"error": "empty text"})
    audio = POLLY.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId=VOICES[language],
        Engine=os.getenv("POLLY_ENGINE", "standard"),
    )["AudioStream"].read()
    _log(route="voice", chars=len(text))
    return _resp(200, {"audio_base64": base64.b64encode(audio).decode("ascii")})


def _stats(item: dict | None) -> dict:
    item = item or {}
    return {"answered": int(item.get("answered", 0)), "correct": int(item.get("correct", 0))}


def comprehension(body: dict) -> dict:
    """One-tap check after a safe window. Only two atomic counters are stored."""
    if not isinstance(body.get("correct"), bool):
        return _resp(400, {"error": "correct must be true or false"})
    if not _take_daily_slot("quiz", QUIZ_CAP):
        _log(route="comprehension", outcome="daily_cap")
        return _resp(429, {"error": "daily_cap"})
    out = TABLE.update_item(
        Key=STATS_KEY,
        UpdateExpression="ADD answered :one, correct :c",
        ExpressionAttributeValues={":one": 1, ":c": 1 if body["correct"] else 0},
        ReturnValues="UPDATED_NEW",
    )
    _log(route="comprehension", outcome="ok")
    return _resp(200, _stats((out or {}).get("Attributes")))


def comprehension_stats() -> dict:
    return _resp(200, _stats(TABLE.get_item(Key=STATS_KEY).get("Item")))


def handler(event: dict, _context) -> dict:
    route = event.get("routeKey", "")
    try:
        body = json.loads(event.get("body") or "{}")
        if event.get("isBase64Encoded"):
            body = json.loads(base64.b64decode(event["body"]))
    except (ValueError, TypeError):
        return _resp(400, {"error": "invalid JSON"})
    if not isinstance(body, dict):
        return _resp(400, {"error": "invalid JSON"})
    if route == "POST /api/chat":
        return chat(body)
    if route == "GET /api/reminders":
        return reminders(event.get("queryStringParameters") or {})
    if route == "POST /api/voice":
        return voice(body)
    if route == "POST /api/warm":
        return warm(body)
    if route == "POST /api/comprehension":
        return comprehension(body)
    if route == "GET /api/comprehension":
        return comprehension_stats()
    if route == "GET /api/health":
        return _resp(200, {"ok": True})
    return _resp(404, {"error": "not found"})
