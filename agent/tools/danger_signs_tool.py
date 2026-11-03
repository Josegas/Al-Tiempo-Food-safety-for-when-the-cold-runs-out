from strands import tool

from agent.rules_engine import check_danger_signs as engine_check
from agent.tools._common import out


@tool
def check_danger_signs(answers: dict[str, bool | None], country: str | None = None) -> str:
    """Escalation for diarrhoea/vomiting. Never diagnose, never give doses.

    Args:
        answers: Map of sign id -> True/False/None (unknown). Ids: LETHARGIC, SUNKEN_EYES,
            CANNOT_DRINK, SKIN_PINCH_SLOW, BLOOD_IN_STOOL.
        country: ISO country code (MX, US, IN, ES, GB...), if known.
    """
    return out(engine_check(answers, country))
