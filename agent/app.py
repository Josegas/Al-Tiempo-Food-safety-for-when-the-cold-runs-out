"""AgentCore Runtime entrypoint.

Payload: {"prompt": "...", "language": "en"|"es", "history": [...optional Strands messages]}
"""

from __future__ import annotations

import json
import logging
import re
import time

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent.agent import build_agent

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("al_tiempo")
app = BedrockAgentCoreApp()
THINKING_RE = re.compile(r"<thinking>.*?</thinking>", re.DOTALL)

FALLBACK = {
    "en": "Sorry, I could not answer right now. Safety rule while you wait: on a hot day, do not keep cooked food out more than 1 hour; if in doubt, throw it away.",
    "es": "Perdón, no pude responder ahora. Regla de seguridad mientras tanto: en día de calor, no dejes comida cocida fuera más de 1 hora; si tienes duda, deséchala.",
}


@app.entrypoint
def invoke(payload: dict) -> dict:
    prompt = (payload or {}).get("prompt", "").strip()
    language = (payload or {}).get("language", "en")
    if not prompt:
        return {"error": "empty prompt"}
    started = time.perf_counter()
    agent, verifier = build_agent(language, payload.get("history"))
    try:
        result = agent(prompt)
    except Exception as exc:  # model/region/throttling errors -> safe fallback, never a stack trace
        log.error(json.dumps({"event": "agent_error", "error": type(exc).__name__}))
        return {"answer": FALLBACK.get(language, FALLBACK["en"]), "error": type(exc).__name__}
    usage = result.metrics.accumulated_usage
    record = {
        "event": "conversation_turn",
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "input_tokens": usage.get("inputTokens", 0),
        "output_tokens": usage.get("outputTokens", 0),
        "verifier_retried": verifier.retried_count,
        "verifier_blocked": verifier.blocked_count,
        "verifier_violations": verifier.violations,
        "tools_used": list(result.metrics.tool_metrics.keys()),
    }
    log.info(json.dumps(record))  # structured log -> CloudWatch Logs Insights / metric filters
    answer = THINKING_RE.sub("", str(result)).strip()
    return {"answer": answer, "metrics": record, "history": agent.messages}


if __name__ == "__main__":
    app.run()
