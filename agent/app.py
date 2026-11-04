"""AgentCore Runtime entrypoint (HTTP protocol: /ping + /invocations on port 8080).

Payload:
  {"prompt": "...", "language": "en"|"es", "demo": true|false,
   "timezone": "America/Mazatlan", "lat": 24.8, "lon": -107.4}

AgentCore routes every request with the same runtimeSessionId to the same microVM, so the
conversation (Strands agent + verifier) is kept in memory per session. Nothing personal is
logged: only latency, tokens, tools and verifier counters.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent.agent import build_agent, clean_answer
from agent.decision import safe_window_decision, shelter_plan_decision
from agent.request_context import RequestSettings, set_current

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("al_tiempo")
app = BedrockAgentCoreApp()

MAX_PROMPT_CHARS = 1000
MAX_SESSIONS = 50  # per microVM; oldest conversations are dropped first
SESSION_TTL_S = 30 * 60

FALLBACK = {
    "en": "Sorry, I could not answer right now. Safety rule while you wait: on a hot day, do not keep cooked food out more than 1 hour; if in doubt, throw it away.",
    "es": "Perdón, no pude responder ahora. Regla de seguridad mientras tanto: en día de calor, no dejes comida cocida fuera más de 1 hora; si tienes duda, deséchala.",
}

_sessions: OrderedDict[str, dict] = OrderedDict()
_lock = threading.Lock()


def _settings(payload: dict, session_id: str | None) -> RequestSettings:
    def num(key: str, lo: float, hi: float) -> float | None:
        try:
            value = float(payload.get(key))
        except (TypeError, ValueError):
            return None
        return value if lo <= value <= hi else None

    demo = payload.get("demo")
    tz = payload.get("timezone")
    return RequestSettings(
        demo=demo if isinstance(demo, bool) else None,
        timezone=tz if isinstance(tz, str) and len(tz) <= 64 else None,
        lat=num("lat", -90, 90),
        lon=num("lon", -180, 180),
        session_id=session_id,
    )


def _get_session(session_id: str | None, language: str, demo: bool | None) -> dict:
    """Same session id -> same agent (multi-turn). Language or mode change -> new agent."""
    now = time.time()
    with _lock:
        for sid in [s for s, v in _sessions.items() if now - v["last"] > SESSION_TTL_S]:
            _sessions.pop(sid, None)
        key = f"{session_id}|{language}|{demo}"
        entry = _sessions.get(key) if session_id else None
        if entry is None:
            agent, verifier = build_agent(language)
            entry = {"agent": agent, "verifier": verifier, "in": 0, "out": 0}
            if session_id:
                _sessions[key] = entry
                while len(_sessions) > MAX_SESSIONS:
                    _sessions.popitem(last=False)
        entry["last"] = now
        if session_id:
            _sessions.move_to_end(key)
        return entry


@app.entrypoint
def invoke(payload: dict, context=None) -> dict:
    payload = payload if isinstance(payload, dict) else {}
    prompt = str(payload.get("prompt", "")).strip()[:MAX_PROMPT_CHARS]
    language = payload.get("language") if payload.get("language") in ("en", "es") else "en"
    if payload.get("warmup") is True:
        # Called when the page opens: AgentCore starts this session's microVM, imports run and the
        # agent is built now, so the user's first real message is answered in ~2 s, not ~6 s.
        # No model call, no tokens.
        session_id = getattr(context, "session_id", None)
        settings = _settings(payload, session_id)
        _get_session(session_id, language, settings.demo)
        log.info(json.dumps({"event": "warmup", "language": language}))
        return {"warm": True}
    if not prompt:
        return {"error": "empty prompt"}

    session_id = getattr(context, "session_id", None)
    settings = _settings(payload, session_id)
    set_current(settings)
    entry = _get_session(session_id, language, settings.demo)
    agent, verifier = entry["agent"], entry["verifier"]
    agent.state.set("session_id", session_id)
    agent.state.set("language", language)

    started = time.perf_counter()
    n_before = len(agent.messages)
    retried_before, blocked_before = verifier.retried_count, verifier.blocked_count
    try:
        result = agent(prompt)
    except Exception as exc:  # model/region/throttling errors -> safe fallback, never a stack trace
        log.error(json.dumps({"event": "agent_error", "error": type(exc).__name__}))
        return {"answer": FALLBACK[language], "error": type(exc).__name__}

    usage = agent.event_loop_metrics.accumulated_usage
    tools = [
        b["toolUse"]["name"]
        for m in agent.messages[n_before:]
        for b in m.get("content", [])
        if "toolUse" in b
    ]
    record = {
        "event": "conversation_turn",
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "input_tokens": usage["inputTokens"] - entry["in"],
        "output_tokens": usage["outputTokens"] - entry["out"],
        "verifier_retried": verifier.retried_count - retried_before,
        "verifier_blocked": verifier.blocked_count - blocked_before,
        "tools_used": tools,
        "demo": demo_flag(settings),
        "language": language,
    }
    entry["in"], entry["out"] = usage["inputTokens"], usage["outputTokens"]
    log.info(json.dumps(record))  # structured log -> CloudWatch Logs Insights / metric filters
    response = {"answer": clean_answer(str(result)), "metrics": record}
    turn = agent.messages[n_before:]
    decision = safe_window_decision(turn) or shelter_plan_decision(turn)
    if decision:  # optional: lets the web draw the timeline (safe window / shelter batches) from the engine's numbers
        response["decision"] = decision
    return response


def demo_flag(settings: RequestSettings) -> bool:
    from agent.forecast import demo_mode

    return demo_mode() if settings.demo is None else settings.demo


if __name__ == "__main__":
    app.run()
