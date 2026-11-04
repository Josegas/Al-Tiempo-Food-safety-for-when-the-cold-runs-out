"""BeforeInvocationEvent hook: adds the matching objection text (rules/objections.yaml) to the
user's message, so the model answers the user's point with official wording.
`BeforeInvocationEvent.messages` is writable (strands-agents 1.x: "Can be modified by hooks")."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from strands.hooks import BeforeInvocationEvent, HookProvider, HookRegistry

from agent.objections import context_note, detect


@dataclass
class ObjectionHook(HookProvider):
    language: str = "en"

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        registry.add_callback(BeforeInvocationEvent, self.on_start)

    def on_start(self, event: BeforeInvocationEvent) -> None:
        state = getattr(event.agent, "state", None)
        user_msgs = [
            m for m in (event.messages or []) if isinstance(m, dict) and m.get("role") == "user"
        ]
        text = " ".join(
            b.get("text", "")
            for m in user_msgs
            for b in m.get("content", [])
            if isinstance(b, dict)
        )
        found = detect(text)
        if state is not None:
            state.set("objections", [o["id"] for o in found])
        note = context_note(found, self.language)
        if note and user_msgs:
            user_msgs[-1]["content"].append({"text": note})
