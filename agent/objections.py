"""Common objections ("it was covered", "I tasted it", "I'll boil it again", "I already ate it").

The CODE decides which ones apply (substring triggers from rules/objections.yaml), not the model.
The matching text (reply + why + source) is handed to the model, which may rephrase it but must
not add facts, and the verifier's safe fallback uses the same text.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

FILE = Path(__file__).resolve().parent.parent / "rules" / "objections.yaml"
RULES_PREFIX = "[rules]"  # context added by code to the user's message; never "typed by the user"
MAX_MATCHES = 2


@lru_cache(maxsize=1)
def load_objections() -> list[dict]:
    return yaml.safe_load(FILE.read_text(encoding="utf-8"))["objections"]


def detect(text: str, limit: int = MAX_MATCHES) -> list[dict]:
    """Objections in the user's words (both languages: people mix them). File order, max `limit`."""
    low = (text or "").lower()
    found = []
    for o in load_objections():
        triggers = o["triggers"].get("es", []) + o["triggers"].get("en", [])
        if any(t.lower() in low for t in triggers):
            found.append(o)
    return found[:limit]


def short_source(o: dict) -> str:
    return o["source_name"].split(" - ")[0]


def sentence(o: dict, lang: str) -> str:
    """Reply + why, in the user's language: the text the fallback shows as is."""
    lang = lang if lang in ("es", "en") else "en"
    return f"{o['reply'][lang]} {o['why'][lang]}"


def context_note(found: list[dict], lang: str) -> str:
    if not found:
        return ""
    lang = lang if lang in ("es", "en") else "en"
    label = {"official": "from", "adapted": "adapted from", "policy": "project policy, not"}
    lines = [
        f"- {o['id']}: {o['reply'][lang]} Reason ({label.get(o['kind'], 'from')} "
        f"{short_source(o)}): {o['why'][lang]}"
        for o in found
    ]
    return (
        f"{RULES_PREFIX} The user's message matches these common objections. After the engine's "
        "decision (if any), answer them with this text. You may rephrase it but do not add facts, "
        "times or limits. Only the reason comes from the source: do not attribute the rest to it. "
        "Do not scold the user.\n" + "\n".join(lines)
    )
