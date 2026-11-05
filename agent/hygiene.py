"""Hygiene tips (rules/hygiene_tips.yaml). The CODE decides if one applies, by words in the user's
message, in the file's priority order; at most 1 per answer. The tip goes next to the answer (API
field `hygiene_tip`), after the main decision: the model never sees it and it never changes it."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

FILE = Path(__file__).resolve().parent.parent / "rules" / "hygiene_tips.yaml"


@lru_cache(maxsize=1)
def load_tips() -> dict:
    return yaml.safe_load(FILE.read_text(encoding="utf-8"))


def pick_tip(text: str, lang: str) -> dict | None:
    low = (text or "").lower()
    lang = lang if lang in ("es", "en") else "en"
    data = load_tips()
    for tip in data["tips"]:
        triggers = tip["triggers"].get("es", []) + tip["triggers"].get("en", [])
        if any(t.lower() in low for t in triggers):
            return {
                "id": tip["id"],
                "tip": tip["tip"][lang],
                "why": tip["why"][lang],
                "source_name": data["source_name"],
                "source_url": data["source_url"],
            }
    return None
