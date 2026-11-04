"""Verifier hook: every clock time or time limit the model writes must come from a tool result.

Flow (Strands hook events, checked against strands-agents 1.63 source):
  BeforeInvocationEvent -> reset what we know for this request.
  AfterToolCallEvent    -> collect allowed times (HH:MM) and limits (minutes) from tool results.
  AfterModelCallEvent   -> if the final answer mentions a time/limit not backed by a tool
                           (this turn's tools, the user's own words, or - in a follow-up with no
                           time of its own - the engine results of the previous turn with tools):
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
# The prompt shows the answer shape with placeholders ("eat it before HH:MM", "<rule / source>").
# Eval bug: with no tool result, the model once copied "antes de las HH:MM" into the answer.
# The prompt's example dialogs use {hora_limite} / {deadline}: copying one is the same bug.
PLACEHOLDER_RE = re.compile(r"\bHH:MM\b|<\s*(rule|regla)\b|\{[a-z_]+\}", re.IGNORECASE)
# Durations up to this size are about food. Bigger numbers (e.g. "24 hours" freezer) are
# still checked against the allowed set.
MAX_RETRIES = 1
# The retry note is appended to the user's message. Its text lists the blocked times, so it must
# never count as "times the user typed" (bug found live: the note approved its own blocked times).
NOTE_PREFIX = "[verifier]"
# Notes added by code (verifier retries, objection text) are not the user's words.
CODE_PREFIXES = (NOTE_PREFIX, "[rules]")


def _user_claims(blocks: list) -> tuple[set[str], set[int]]:
    times: set[str] = set()
    minutes: set[int] = set()
    for block in blocks:
        text = block.get("text", "") if isinstance(block, dict) else ""
        if text and not text.startswith(CODE_PREFIXES):
            t, m = extract_claims(text)
            times |= t
            minutes |= m
    return times, minutes


def _current_user_claims(messages: list) -> tuple[set[str], set[int]] | None:
    """Times/durations in the user's latest typed message (None if there is none)."""
    for msg in reversed(messages or []):
        if not isinstance(msg, dict) or msg.get("role") != "user":
            continue
        blocks = [b for b in msg.get("content", []) if isinstance(b, dict) and "text" in b]
        if blocks:
            return _user_claims(blocks)
    return None


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
        "{window}{point}If you are unsure, it is safer to throw the food away."
    ),
    "es": (
        "Para no darte una hora equivocada, te respondo solo con lo que dicen las reglas oficiales. "
        "{window}{point}Si tienes duda, es más seguro tirar la comida."
    ),
}
# Used instead when the first one would repeat the previous fallback word for word (bug seen live:
# two follow-ups got the same generic answer twice in a row).
SAFE_TEMPLATE_AGAIN = {
    "en": (
        "I'll stick to the official rules so I don't give you a wrong time. {window}{point}"
        "If you tell me what food it is and when you made it, I'll check it again with the rules."
    ),
    "es": (
        "Me quedo con lo que dicen las reglas oficiales para no darte una hora equivocada. "
        "{window}{point}Si me dices qué comida es y a qué hora la preparaste, la reviso otra vez "
        "con las reglas."
    ),
}


@dataclass
class VerifierHook(HookProvider):
    language: str = "en"
    allowed_times: set[str] = field(default_factory=set)
    allowed_minutes: set[int] = field(default_factory=set)
    # Engine results of this turn, and of the last earlier turn that called tools (same session).
    turn_tool_times: set[str] = field(default_factory=set)
    turn_tool_minutes: set[int] = field(default_factory=set)
    session_times: set[str] = field(default_factory=set)
    session_minutes: set[int] = field(default_factory=set)
    last_safe: str = ""  # last fallback text: never repeated word for word
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
        if self.turn_tool_times or self.turn_tool_minutes:
            self.session_times = set(self.turn_tool_times)
            self.session_minutes = set(self.turn_tool_minutes)
        self.turn_tool_times, self.turn_tool_minutes = set(), set()
        self.last_window = None
        self.retries = 0
        # Times the user wrote (e.g. "I cooked at 12:30") may be repeated back.
        for msg in event.messages or []:
            if isinstance(msg, dict):
                t, m = _user_claims(msg.get("content", []))
                self.allowed_times |= t
                self.allowed_minutes |= m

    def on_tool_result(self, event: AfterToolCallEvent) -> None:
        t, m = collect_allowed(event.result)
        self.allowed_times |= t
        self.allowed_minutes |= m
        self.turn_tool_times |= t
        self.turn_tool_minutes |= m
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
        # Also accept times the user typed in this conversation (never the verifier's own notes).
        for msg in event.agent.messages:
            if msg.get("role") == "user":
                t, m = _user_claims(msg.get("content", []))
                self.allowed_times |= t
                self.allowed_minutes |= m  # durations the user said ("hace 5 horas")
        allowed_t, allowed_m = set(self.allowed_times), set(self.allowed_minutes)
        # Follow-up with no time of its own ("but it was covered", "I tasted it"): the engine's
        # results from the previous turn with tools still hold. A message with its own time or
        # duration is about new data and must go through the engine again.
        current = _current_user_claims(event.agent.messages)
        if current is not None and not current[0] and not current[1]:
            allowed_t |= self.session_times
            allowed_m |= self.session_minutes
        bad = find_unbacked(text, allowed_t, allowed_m)
        if PLACEHOLDER_RE.search(text):
            bad["placeholder"] = "copied a template placeholder; with no tool time, give no time"
        if not bad["times"] and not bad["minutes"] and "placeholder" not in bad:
            return
        self.violations.append(bad)

        if self.retries < MAX_RETRIES:
            self.retries += 1
            self.retried_count += 1
            note = (
                f"{NOTE_PREFIX} Your last answer used times/limits that no tool returned in this "
                f"turn: {bad}. Rewrite it using ONLY the exact times and limits from this turn's "
                "tool results. If a time comes from an earlier answer (the user didn't understand "
                "or asks again), call the tool again with the same data instead of repeating it."
            )
            last = event.agent.messages[-1] if event.agent.messages else None
            if last and last.get("role") == "user":
                last["content"].append({"text": note})
            event.retry = True
            return

        # Still wrong after retry: replace the answer in place with a safe template.
        self.blocked_count += 1
        state = getattr(event.agent, "state", None)
        session_window = state.get("last_window") if state is not None else None
        objections = (state.get("objections") if state is not None else None) or []
        resp.message["content"][:] = [{"text": self.safe_answer(session_window, objections)}]

    # -- helpers --------------------------------------------------------------
    def safe_answer(
        self, session_window: dict | None = None, objection_ids: list[str] | None = None
    ) -> str:
        lang = self.language if self.language in SAFE_TEMPLATE else "en"
        window = ""
        if not self.last_window and session_window:
            window = _previous_window_sentence(session_window, lang)
        if self.last_window:
            src = (self.last_window.get("deciding_source") or self.last_window["sources"][-1])[
                "source_name"
            ].split(" - ")[0]  # short publisher name: "U.S. FDA", "WHO"
            hhmm = self.last_window["eat_by_hhmm"]
            expired = self.last_window.get("status") == "discard_now"
            if lang == "en":
                window = (
                    f"According to {src}, the time limit has passed: the safest choice is not to "
                    "eat it and to throw it away. "
                    if expired
                    else f"According to {src}, eat it before {hhmm} or throw it away. "
                )
            else:
                window = (
                    f"Según {src}, ya pasó el tiempo límite: lo más seguro es no comerlo y tirarlo. "
                    if expired
                    else f"Según {src}, cómelo antes de las {hhmm} o deséchalo. "
                )
        point = "".join(f"{s} " for s in _objection_sentences(objection_ids or [], lang))
        text = SAFE_TEMPLATE[lang].format(window=window, point=point)
        if text == self.last_safe:
            text = SAFE_TEMPLATE_AGAIN[lang].format(window=window, point=point)
        self.last_safe = text
        return text


def _objection_sentences(ids: list[str], lang: str) -> list[str]:
    """The user's point (detected in code), answered with the rules' own text."""
    from agent.objections import load_objections, sentence

    by_id = {o["id"]: o for o in load_objections()}
    return [sentence(by_id[i], lang) for i in ids if i in by_id]


def _previous_window_sentence(w: dict, lang: str) -> str:
    """Follow-up turn with no tool call ("I didn't understand"): repeat the session's last engine
    decision, tied to its cooking time so it can't be read as being about another dish.
    The deadline is compared with the clock in code (not by the model)."""
    from datetime import datetime

    from agent.tools._common import now_local

    if w.get("time_source") == "unknown" or not w.get("cooked_at_hhmm") or not w.get("eat_by"):
        return ""  # the engine assumed "cooked long ago": no real time to repeat
    try:
        expired = now_local() >= datetime.fromisoformat(w["eat_by"])
    except (ValueError, TypeError):
        return ""
    src = str(w.get("source_name", "")).split(" - ")[0] or (
        "the rules" if lang == "en" else "las reglas"
    )
    cooked, hhmm = w["cooked_at_hhmm"], w["eat_by_hhmm"]
    if lang == "en":
        verdict = (
            "the time limit has passed: the safest choice is not to eat it and to throw it away"
            if expired
            else f"eat it before {hhmm} or throw it away"
        )
        return f"For the food you cooked at {cooked}: according to {src}, {verdict}. "
    verdict = (
        "ya pasó el tiempo límite: lo más seguro es no comerlo y tirarlo"
        if expired
        else f"cómelo antes de las {hhmm} o deséchalo"
    )
    return f"Para lo que cocinaste a las {cooked}: según {src}, {verdict}. "
