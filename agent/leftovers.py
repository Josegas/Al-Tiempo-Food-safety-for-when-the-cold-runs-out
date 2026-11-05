"""What to do with food that must be thrown away (rules/leftover_tips.yaml).

The CODE decides: only when this turn's safe window says "discard_now". The note goes next to
the answer (API field `leftover_tip`), after the decision: the model never sees it and it never
changes the decision. Never suggests feeding it to animals.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

FILE = Path(__file__).resolve().parent.parent / "rules" / "leftover_tips.yaml"


@lru_cache(maxsize=1)
def load_leftover_tips() -> dict:
    return yaml.safe_load(FILE.read_text(encoding="utf-8"))


def pick_leftover_tip(decision: dict | None, lang: str) -> dict | None:
    if not decision or decision.get("kind") != "safe_window":
        return None
    if decision.get("status") != "discard_now" or decision.get("cooked_known") is False:
        return None  # unknown cooking time: the answer asks for it first
    lang = lang if lang in ("es", "en") else "en"
    data = load_leftover_tips()
    tip = data["tips"][0]
    return {
        "id": tip["id"],
        "tip": tip["tip"][lang],
        "why": tip["why"][lang],
        "source_name": data["source_name"],
        "source_url": data["source_url"],
    }
