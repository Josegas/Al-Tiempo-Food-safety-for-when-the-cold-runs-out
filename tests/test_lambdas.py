"""API and reminder Lambdas with fake AWS clients (no network, no AWS account)."""

import base64
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parent.parent / "infra" / "lambdas"
SESSION = "web-" + "a" * 40


def load(name: str, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("TABLE_NAME", "t")
    monkeypatch.setenv("RUNTIME_ARN", "arn:aws:bedrock-agentcore:us-east-1:1:runtime/x")
    spec = importlib.util.spec_from_file_location(f"lambda_{name}", ROOT / name / "handler.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeTable:
    def __init__(self, cap_reached=False):
        self.cap_reached, self.items = cap_reached, []

    def update_item(self, **kw):
        if self.cap_reached:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem")

    def put_item(self, Item):
        self.items.append(Item)

    def query(self, **kw):
        return {"Items": [{"reminder_id": "r1", "message": "Eat", "at_local": "12:45",
                           "delivered_at": "2026-11-04T19:46:00Z", "delay_s": 3, "pk": "x"}]}  # fmt: skip


def event(route, body=None, qs=None):
    return {"routeKey": route, "body": json.dumps(body) if body is not None else None,
            "queryStringParameters": qs}  # fmt: skip


@pytest.fixture
def api(monkeypatch):
    mod = load("api", monkeypatch)
    mod.TABLE = FakeTable()
    calls = []

    def invoke_agent_runtime(**kw):
        calls.append(kw)
        body = {
            "answer": "Eat it before 13:00.",
            "metrics": {"tools_used": ["compute_safe_window"]},
        }
        return {"response": io.BytesIO(json.dumps(body).encode())}

    mod.AGENTCORE = SimpleNamespace(invoke_agent_runtime=invoke_agent_runtime)
    mod.POLLY = SimpleNamespace(synthesize_speech=lambda **kw: {"AudioStream": io.BytesIO(b"mp3")})
    mod._calls = calls
    return mod


def test_chat_ok_passes_session_and_demo_default(api):
    r = api.handler(event("POST /api/chat", {"prompt": "hola", "session_id": SESSION}), None)
    assert r["statusCode"] == 200
    assert "13:00" in json.loads(r["body"])["answer"]
    call = api._calls[0]
    assert call["runtimeSessionId"] == SESSION
    assert json.loads(call["payload"])["demo"] is True


@pytest.mark.parametrize(
    "body",
    [{"prompt": "", "session_id": SESSION}, {"prompt": "x" * 1001, "session_id": SESSION},
     {"prompt": "hola", "session_id": "short"}, {"prompt": "hola", "session_id": "bad id with spaces" * 3}],
)  # fmt: skip
def test_chat_rejects_bad_input(api, body):
    assert api.handler(event("POST /api/chat", body), None)["statusCode"] == 400


def test_daily_cap_returns_429_with_friendly_message(api):
    api.TABLE = FakeTable(cap_reached=True)
    r = api.handler(
        event("POST /api/chat", {"prompt": "hola", "session_id": SESSION, "language": "es"}), None
    )
    assert r["statusCode"] == 429 and "mañana" in json.loads(r["body"])["answer"]


def test_agentcore_failure_returns_safe_message(api):
    def boom(**kw):
        raise TimeoutError()

    api.AGENTCORE = SimpleNamespace(invoke_agent_runtime=boom)
    r = api.handler(
        event("POST /api/chat", {"prompt": "hola", "session_id": SESSION, "language": "es"}), None
    )
    assert r["statusCode"] == 502 and "tira la comida" in json.loads(r["body"])["answer"]


def test_reminders_only_returns_public_fields(api):
    r = api.handler(event("GET /api/reminders", qs={"session_id": SESSION}), None)
    rem = json.loads(r["body"])["reminders"][0]
    assert rem["at_local"] == "12:45" and "pk" not in rem


def test_voice(api):
    r = api.handler(event("POST /api/voice", {"text": "Hola", "language": "es"}), None)
    assert base64.b64decode(json.loads(r["body"])["audio_base64"]) == b"mp3"


def test_unknown_route_and_bad_json(api):
    assert api.handler(event("GET /api/nope"), None)["statusCode"] == 404
    assert api.handler({"routeKey": "POST /api/chat", "body": "{bad"}, None)["statusCode"] == 400


def test_reminder_lambda_stores_with_ttl_and_measures_delay(monkeypatch):
    mod = load("reminder", monkeypatch)
    mod.TABLE = FakeTable()
    mod.handler({"reminder_id": "r1", "session_id": SESSION, "message": "Eat the beans",
                 "channel": "sms", "contact": "+5210000000000", "at_local": "12:45",
                 "fire_utc": "2026-11-04T19:45:00Z"}, None)  # fmt: skip
    item = mod.TABLE.items[0]
    assert item["pk"] == f"SESSION#{SESSION}" and item["expires_at"] > 0
    assert "delay_s" in item
    assert "contact" not in item  # phone number is never stored


def test_warm_starts_session_without_prompt(api):
    r = api.handler(event("POST /api/warm", {"session_id": SESSION, "language": "es"}), None)
    assert r["statusCode"] == 200 and json.loads(r["body"])["warm"] is True
    payload = json.loads(api._calls[0]["payload"])
    assert payload["warmup"] is True and "prompt" not in payload
    assert api._calls[0]["runtimeSessionId"] == SESSION


def test_warm_has_its_own_daily_cap_and_validation(api):
    assert api.handler(event("POST /api/warm", {"session_id": "short"}), None)["statusCode"] == 400
    api.TABLE = FakeTable(cap_reached=True)
    r = api.handler(event("POST /api/warm", {"session_id": SESSION}), None)
    assert r["statusCode"] == 429 and api._calls == []
