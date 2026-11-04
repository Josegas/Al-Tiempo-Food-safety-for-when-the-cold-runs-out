"""Verifier hook: every clock time or time limit the model writes must come from a tool result.

Flow (Strands hook events, checked against strands-agents 1.63 source):
  BeforeInvocationEvent -> reset what we know for this request.
  AfterToolCallEvent    -> collect allowed times (HH:MM) and limits (minutes) from tool results.
  AfterModelCallEvent   -> if the final answer mentions a time/limit not backed by a tool:
                           1st time: ask the model to retry with a correction note;
                           after that: replace the answer with a safe template.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from strands.hooks import (
    AfterModelCallEvent,
    AfterToolCallEvent,
    BeforeInvocationEvent,
    HookProvider,
    HookRegistry,
)

from agent.rules_engine import load_rules

# 13:45, 1:45, 01:45 pm, 1:45 p.m.  (minutes required so "2 hours" isn't read as a clock time)
TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*([ap]\.?\s?m\.?)?", re.IGNORECASE)
# "2 hours", "1 hora", "90 minutes", "30 min", "1.5 h"
DURATION_RE = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(hours?|hrs?|horas?|h|minutes?|minutos?|mins?)\b", re.IGNORECASE
)
ISO_TIME_RE = re.compile(r"T(\d{2}):(\d{2})")
HHMM_RE = re.compile(r"^(\d{2}):(\d{2})$")
# Durations up to this size are about food. Bigger numbers (e.g. "24 hours" freezer) are
# still checked against the allowed set.
MAX_RETRIES = 1


def _normalize_time(h: int, m: int, ampm: str | None) -> str:
    if ampm:
        pm = ampm.lower().startswith("p")
        if pm and h < 12:
            h += 12
        if not pm and h == 12:
            h = 0
    return f"{h:02d}:{m:02d}"


def extract_claims(text: str) -> tuple[set[str], set[int]]:
    """Clock times (HH:MM, 24h) and durations (minutes) mentioned in text."""
    times = {
        _normalize_time(int(h), int(m), ap)
        for h, m, ap in TIME_RE.findall(text)
        if int(h) < 24 and int(m) < 60
    }
    minutes: set[int] = set()
    for num, unit in DURATION_RE.findall(text):
        value = float(num.replace(",", "."))
        is_hour = unit.lower().startswith("h")
        minutes.add(int(round(value * 60)) if is_hour else int(round(value)))
    return times, minutes


def find_unbacked(text: str, allowed_times: set[str], allowed_minutes: set[int]) -> dict:
    times, minutes = extract_claims(text)
    return {
        "times": sorted(times - allowed_times),
        "minutes": sorted(minutes - allowed_minutes),
    }


def _walk(obj: Any, times: set[str], minutes: set[int]) -> None:
    rules = load_rules()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if "minutes" in k and isinstance(v, int | float):
                minutes.add(int(v))
            if k == "rule_ids" and isinstance(v, list):
                for rid in v:
                    lim = rules.get(rid).limit_minutes if rid in rules else None
                    if lim:
                        minutes.add(int(lim))
            _walk(v, times, minutes)
    elif isinstance(obj, list):
        for v in obj:
            _walk(v, times, minutes)
    elif isinstance(obj, str):
        for h, m in ISO_TIME_RE.findall(obj):
            times.add(f"{h}:{m}")
        if HHMM_RE.match(obj):
            times.add(obj)
        # tool results arrive as JSON text
        if obj.startswith(("{", "[")):
            try:
                _walk(json.loads(obj), times, minutes)
            except ValueError:
                pass


def collect_allowed(tool_result: Any) -> tuple[set[str], set[int]]:
    times: set[str] = set()
    minutes: set[int] = set()
    _walk(tool_result, times, minutes)
    return times, minutes


SAFE_TEMPLATE = {
    "en": (
        "To avoid giving you a wrong time, here is only what the official rules say. "
        "{window}If you are unsure, it is safer to throw the food away."
    ),
    "es": (
        "Para no darte una hora equivocada, te respondo solo con lo que dicen las reglas oficiales. "
        "{window}Si tienes duda, es más seguro tirar la comida."
    ),
}


@dataclass
class VerifierHook(HookProvider):
    language: str = "en"
    allowed_times: set[str] = field(default_factory=set)
    allowed_minutes: set[int] = field(default_factory=set)
    last_window: dict | None = None
    retries: int = 0
    blocked_count: int = 0  # metrics: unsafe answers blocked
    retried_count: int = 0
    violations: list[dict] = field(default_factory=list)  # for logs / evals

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeInvocationEvent, self.on_start)
        registry.add_callback(AfterToolCallEvent, self.on_tool_result)
        registry.add_callback(AfterModelCallEvent, self.on_model_response)

    # -- events ---------------------------------------------------------------
    def on_start(self, event: BeforeInvocationEvent) -> None:
        self.allowed_times = set()
        self.allowed_minutes = set()
        self.last_window = None
        self.retries = 0
        # Times the user wrote (e.g. "I cooked at 12:30") may be repeated back.
        for msg in event.messages or []:
            for block in msg.get("content", []) if isinstance(msg, dict) else []:
                if "text" in block:
                    t, m = extract_claims(block["text"])
                    self.allowed_times |= t
                    self.allowed_minutes |= m

    def on_tool_result(self, event: AfterToolCallEvent) -> None:
        t, m = collect_allowed(event.result)
        self.allowed_times |= t
        self.allowed_minutes |= m
        for block in (event.result or {}).get("content", []):
            text = block.get("text", "")
            if '"eat_by_hhmm"' in text:
                try:
                    self.last_window = json.loads(text)
                except ValueError:
                    pass

    def on_model_response(self, event: AfterModelCallEvent) -> None:
        resp = event.stop_response
        if resp is None or resp.stop_reason != "end_turn":
            return  # tool-use turns are checked later, on the final answer
        text = "".join(b.get("text", "") for b in resp.message.get("content", []))
        # Also accept times the user typed in this conversation.
        for msg in event.agent.messages:
            if msg.get("role") == "user":
                for block in msg.get("content", []):
                    if "text" in block:
                        t, m = extract_claims(block["text"])
                        self.allowed_times |= t
                        self.allowed_minutes |= m  # durations the user said ("hace 5 horas")
        bad = find_unbacked(text, self.allowed_times, self.allowed_minutes)
        if not bad["times"] and not bad["minutes"]:
            return
        self.violations.append(bad)

        if self.retries < MAX_RETRIES:
            self.retries += 1
            self.retried_count += 1
            note = (
                "[verifier] Your last answer used times/limits that no tool returned: "
                f"{bad}. Rewrite it using ONLY the exact times and limits from the tool results."
            )
            last = event.agent.messages[-1] if event.agent.messages else None
            if last and last.get("role") == "user":
                last["content"].append({"text": note})
            event.retry = True
            return

        # Still wrong after retry: replace the answer in place with a safe template.
        self.blocked_count += 1
        resp.message["content"][:] = [{"text": self.safe_answer()}]

    # -- helpers --------------------------------------------------------------
    def safe_answer(self) -> str:
        lang = self.language if self.language in SAFE_TEMPLATE else "en"
        window = ""
        if self.last_window:
            src = (self.last_window.get("deciding_source") or self.last_window["sources"][-1])[
                "source_name"
            ].split(" - ")[0]  # short publisher name: "U.S. FDA", "WHO"
            hhmm = self.last_window["eat_by_hhmm"]
            expired = self.last_window.get("status") == "discard_now"
            if lang == "en":
                window = (
                    f"According to {src}, the time limit has passed: throw it away now. "
                    if expired
                    else f"According to {src}, eat it before {hhmm} or throw it away. "
                )
            else:
                window = (
                    f"Según {src}, ya pasó el tiempo límite: deséchalo ahora. "
                    if expired
                    else f"Según {src}, cómelo antes de las {hhmm} o deséchalo. "
                )
        return SAFE_TEMPLATE[lang].format(window=window)
