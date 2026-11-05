import pytest

from agent.hooks.verifier import extract_claims
from agent.objections import RULES_PREFIX, context_note, detect, load_objections
from agent.rules_engine import load_rules


@pytest.mark.parametrize(
    "text,expected",
    [
        ("pero estaban tapados", "COVERED"),
        ("but it was covered with a lid", "COVERED"),
        ("los probé y estaban buenos", "SMELL_TASTE"),
        ("se me olvido el arroz pero huele bien", "SMELL_TASTE"),
        ("si los hiervo otra vez ya quedan bien no?", "REHEAT"),
        ("my grandmother says if you boil food again all the germs die", "REHEAT"),
        ("si le echo limon o chile al guisado ya no se echa a perder verdad?", "LIME_CHILI"),
        ("toda la vida hemos dejado la comida afuera y nunca nos ha pasado nada", "ALWAYS_DONE"),
        ("ya me lo comí", "ALREADY_ATE"),
        ("entonces ¿se lo doy al perro?", "ANIMALS"),
    ],
)
def test_objections_are_detected_in_code(text, expected):
    assert expected in [o["id"] for o in detect(text)]


@pytest.mark.parametrize(
    "text",
    [
        "Hice frijoles a las 12:00, ¿hasta qué hora?",
        "I cooked chicken curry at 9:00",
        "hice chiles rellenos a las 11",
        "ya comimos y sobró arroz",
    ],
)
def test_plain_questions_trigger_nothing(text):
    assert detect(text) == []


def test_every_objection_has_reply_why_and_a_source_without_times():
    for o in load_objections():
        for lang in ("es", "en"):
            assert o["reply"][lang] and o["why"][lang] and o["triggers"][lang], o["id"]
            # times and limits only come from the engine
            assert extract_claims(o["reply"][lang] + " " + o["why"][lang]) == (set(), set()), o[
                "id"
            ]
        assert o["why_text"] and o["source_url"].startswith("https://") and o["verified_on"]
        assert o["kind"] in ("official", "adapted", "policy")


def test_context_note_is_marked_as_code_not_user():
    note = context_note(detect("pero estaban tapados"), "es")
    assert note.startswith(RULES_PREFIX) and "Taparla no la enfría" in note
    assert "Reason (adapted from WHO)" in note
    assert context_note([], "es") == ""


def test_every_food_rule_has_a_why_in_both_languages():
    for rule in load_rules().values():
        assert rule.why_in("es") and rule.why_in("en"), rule.id
