import re

import pytest

from agent.hooks.verifier import extract_claims
from agent.hygiene import load_tips, pick_tip


@pytest.mark.parametrize(
    "text,expected",
    [
        ("voy a hacer ensalada de lechuga y jitomate para el comedor", "WASH_PRODUCE"),
        ("corte pollo crudo y luego el tomate en la misma tabla", "SEPARATE_RAW"),
        ("I cut raw chicken and then the salad on the same board", "SEPARATE_RAW"),  # priority
        ("antes de cocinar, ¿cómo me lavo las manos?", "WASH_HANDS"),
        ("can I use tap water for the formula?", "SAFE_WATER"),
        ("Hice frijoles a las 12:00, ¿hasta qué hora?", None),
        ("se fue la luz a las 7 y tengo leche, pollo crudo y un guisado", None),
    ],
)
def test_the_code_decides_which_tip_applies(text, expected):
    tip = pick_tip(text, "es")
    assert (tip or {}).get("id") == expected


def test_at_most_one_tip_in_the_users_language():
    tip = pick_tip("ensalada de fruta en la misma tabla", "en")
    assert tip["id"] == "SEPARATE_RAW" and tip["tip"].startswith("Use one board")
    assert tip["source_url"].startswith("https://www.who.int/")


def test_tips_are_backed_and_have_no_times_or_chemical_amounts():
    data = load_tips()
    assert data["source_url"].startswith("https://") and data["verified_on"]
    amounts = re.compile(r"\d|ml\b|gotas|drops|cucharad|teaspoon|%")
    for tip in data["tips"]:
        assert tip["verified_text"] and tip["why_text"], tip["id"]
        for lang in ("es", "en"):
            text = tip["tip"][lang] + " " + tip["why"][lang]
            assert not amounts.search(text), tip["id"]
            assert extract_claims(text) == (set(), set()), tip["id"]
        if "desinfectante" in tip["tip"]["es"]:
            assert "etiqueta" in tip["tip"]["es"] and "label" in tip["tip"]["en"]
