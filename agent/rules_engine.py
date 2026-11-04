"""Deterministic food-safety rules engine.

Design principle: the model talks and explains; official rules decide; when in doubt, the
safest option. Nothing in this module calls an LLM or the network. Every number comes from
rules/food_rules.yaml, and every result says which rules and assumptions produced it.
"""

from __future__ import annotations

import math
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"

ROOM_FOODS = {"cooked_food", "cooked_rice", "infant_formula"}
CHILD_AUDIENCES = {"infant", "young_child"}
REMINDER_LEAD_MINUTES = 15


class RuleNotAllowedError(RuntimeError):
    """Raised when a rule is unverified and unverified rules are not allowed."""


@dataclass(frozen=True)
class Rule:
    id: str
    description: str
    limit_minutes: int | None
    source_name: str
    source_url: str
    verified_on: str | None
    unverified: bool
    kind: str = "official"
    hot_threshold_c: float | None = None
    hot_hold_min_c: float | None = None

    def source(self) -> dict:
        return {
            "rule_id": self.id,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "verified_on": self.verified_on,
            "unverified": self.unverified,
            "kind": self.kind,
        }


@lru_cache(maxsize=1)
def load_rules(path: str | None = None) -> dict[str, Rule]:
    file = Path(path) if path else RULES_DIR / "food_rules.yaml"
    data = yaml.safe_load(file.read_text(encoding="utf-8"))
    rules: dict[str, Rule] = {}
    for raw in data["rules"]:
        rules[raw["id"]] = Rule(
            id=raw["id"],
            description=raw["description"],
            limit_minutes=raw.get("limit_minutes"),
            source_name=raw["source_name"],
            source_url=raw["source_url"],
            verified_on=raw.get("verified_on"),
            unverified=bool(raw.get("unverified", True)),
            kind=raw.get("kind", "official"),
            hot_threshold_c=raw.get("hot_threshold_c"),
            hot_hold_min_c=raw.get("hot_hold_min_c"),
        )
    return rules


def _allow_unverified() -> bool:
    return os.getenv("ALLOW_UNVERIFIED_RULES", "false").lower() == "true"


def get_rule(rule_id: str) -> Rule:
    rule = load_rules()[rule_id]
    if rule.unverified and not _allow_unverified():
        raise RuleNotAllowedError(
            f"Rule {rule_id} is not verified on its official source yet. "
            "Verify it or set ALLOW_UNVERIFIED_RULES=true (dev/demo only)."
        )
    return rule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HourlyTemps = list[tuple[datetime, float]]


def _max_temp_between(temps: HourlyTemps | None, start: datetime, end: datetime) -> float | None:
    """Max forecast temperature for the hours that overlap [start, end]. None if no data."""
    if not temps:
        return None
    hour_start = start.replace(minute=0, second=0, microsecond=0)
    values = [t for ts, t in temps if hour_start <= ts <= end]
    return max(values) if values else None


def _fmt(dt: datetime) -> str:
    return dt.strftime("%H:%M")


@dataclass
class SafeWindow:
    food_type: str
    cooked_at: str
    limit_minutes: int
    eat_by: str  # ISO datetime: eat before this, discard after it
    eat_by_hhmm: str
    reminder_at: str
    serve_immediately: bool
    keep_leftovers: bool
    rule_ids: list[str]
    sources: list[dict]
    assumptions: list[str] = field(default_factory=list)
    unverified_rules_used: bool = False
    # Status at `now`: "eat_before_deadline" or "discard_now" (deadline already passed).
    status: str = "eat_before_deadline"
    minutes_left: int | None = None
    # The rule whose deadline is eat_by (the one to cite: "According to <source>...").
    deciding_source: dict = field(default_factory=dict)
    # Why: hottest forecast hour in the window (None = no forecast -> assumed hot).
    max_temp_c: float | None = None
    hot_threshold_c: float = 32.0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# 1. Safe window (core feature) + 4. strict mode for babies / young children
# ---------------------------------------------------------------------------


def compute_safe_window(
    food_type: str | None,
    cooked_at: datetime,
    audience: str | None = "general",
    hourly_temps: HourlyTemps | None = None,
    feeding_started_at: datetime | None = None,
    now: datetime | None = None,
) -> SafeWindow:
    """Latest time to eat food kept at room temperature (no fridge).

    Applies every rule that matches and keeps the SHORTEST limit (most conservative).
    Missing data -> worst reasonable case.
    """
    assumptions: list[str] = []
    applied: list[Rule] = []

    if food_type not in ROOM_FOODS:
        assumptions.append(
            f"Food type '{food_type}' not recognised: treated as cooked perishable food."
        )
        food_type = "cooked_food"

    if audience is None:
        audience = "general"

    # Base rules for any cooked food at room temperature.
    applied += [get_rule("WHO_COOKED_2H"), get_rule("FDA_2H")]

    # Heat: if any forecast hour in the 2-hour window is above 32 °C -> 1 hour.
    hot = get_rule("FDA_HOT_1H")
    max_t = _max_temp_between(hourly_temps, cooked_at, cooked_at + timedelta(minutes=120))
    if max_t is None:
        assumptions.append("No temperature forecast available: assumed hot day (> 32 °C).")
        applied.append(hot)
    elif max_t > hot.hot_threshold_c:
        assumptions.append(f"Forecast reaches {max_t:.1f} °C (> {hot.hot_threshold_c:.0f} °C).")
        applied.append(hot)
    else:
        assumptions.append(f"Forecast max {max_t:.1f} °C (not above {hot.hot_threshold_c:.0f} °C).")

    if food_type == "cooked_rice":
        applied.append(get_rule("NHS_RICE_1H"))

    serve_immediately = False
    keep_leftovers = True
    start = cooked_at

    if food_type == "infant_formula":
        applied.append(get_rule("CDC_FORMULA_2H"))
        keep_leftovers = False
        if feeding_started_at is not None:
            feed_rule = get_rule("CDC_FORMULA_FEED_1H")
            applied.append(feed_rule)

    if audience in CHILD_AUDIENCES or food_type == "infant_formula":
        applied.append(get_rule("POLICY_CHILD_STRICT"))
        serve_immediately = True
        keep_leftovers = False
        assumptions.append("Strict mode for babies/young children: serve now, keep no leftovers.")

    # Deadline = earliest deadline among all applied rules.
    deadlines: list[tuple[datetime, Rule]] = []
    for r in applied:
        if r.limit_minutes is None:
            continue
        base = feeding_started_at if r.id == "CDC_FORMULA_FEED_1H" else start
        deadlines.append((base + timedelta(minutes=r.limit_minutes), r))
    eat_by = min(d for d, _ in deadlines)
    deciding = next(r for d, r in deadlines if d == eat_by)  # first = official before policy
    limit = int((eat_by - start).total_seconds() // 60)

    lead = min(REMINDER_LEAD_MINUTES, max(limit // 4, 1))
    reminder_at = eat_by - timedelta(minutes=lead)

    unique = list(dict.fromkeys(applied))
    return SafeWindow(
        food_type=food_type,
        cooked_at=cooked_at.isoformat(),
        limit_minutes=limit,
        eat_by=eat_by.isoformat(),
        eat_by_hhmm=_fmt(eat_by),
        reminder_at=reminder_at.isoformat(),
        serve_immediately=serve_immediately,
        keep_leftovers=keep_leftovers,
        rule_ids=[r.id for r in unique],
        sources=[r.source() for r in unique],
        assumptions=assumptions,
        unverified_rules_used=any(r.unverified for r in unique),
        **_status(eat_by, now),
        deciding_source=deciding.source(),
        max_temp_c=None if max_t is None else round(max_t, 1),
        hot_threshold_c=hot.hot_threshold_c,
    )


def _status(eat_by: datetime, now: datetime | None) -> dict:
    if now is None:
        return {}
    left = int((eat_by - now).total_seconds() // 60)
    return {
        "status": "discard_now" if left <= 0 else "eat_before_deadline",
        "minutes_left": max(left, 0),
    }


# ---------------------------------------------------------------------------
# 3. Power-outage mode
# ---------------------------------------------------------------------------


def track_outage(
    outage_started_at: datetime,
    now: datetime,
    fridge_door_opened: bool | None = None,
    freezer_fullness: str | None = None,
) -> dict:
    """What is still within the official outage rules and what is not."""
    assumptions: list[str] = []
    fridge = get_rule("FDA_OUTAGE_FRIDGE_4H")

    if freezer_fullness == "full":
        freezer = get_rule("FDA_OUTAGE_FREEZER_FULL_48H")
    else:
        if freezer_fullness not in ("half",):
            assumptions.append("Freezer fullness unknown: assumed half full (24 h).")
        freezer = get_rule("FDA_OUTAGE_FREEZER_HALF_24H")

    fridge_until = outage_started_at + timedelta(minutes=fridge.limit_minutes)
    freezer_until = outage_started_at + timedelta(minutes=freezer.limit_minutes)
    elapsed = int((now - outage_started_at).total_seconds() // 60)

    door_rule_holds = fridge_door_opened is False
    if fridge_door_opened is None:
        assumptions.append("Unknown if the fridge door was opened: assumed it was.")
    if not door_rule_holds:
        assumptions.append(
            "The 4-hour rule assumes the door stayed closed. With the door opened, "
            "check with a thermometer; if you cannot, treat perishables as unsafe early."
        )

    fridge_ok = now < fridge_until and door_rule_holds
    freezer_ok = now < freezer_until and fridge_door_opened is not True
    # A deadline is only given when its rule applies (door kept closed). Otherwise there is no
    # time to give: the model can't relay one, and the verifier blocks any time it invents.
    # (Eval found it: "door opened" -> the model said "safe until 15:00 if the thermometer...".)
    fridge_time = door_rule_holds
    freezer_time = fridge_door_opened is not True

    return {
        "summary": outage_summary(
            now, fridge_until, freezer_until, fridge_ok, freezer_ok, freezer.limit_minutes // 60
        ),
        "elapsed_minutes": max(elapsed, 0),
        "fridge_safe_until": fridge_until.isoformat() if fridge_time else None,
        "fridge_safe_until_hhmm": _fmt(fridge_until) if fridge_time else None,
        "fridge_status": "ok" if fridge_ok else "discard_perishables_or_check_thermometer",
        "freezer_safe_until": freezer_until.isoformat() if freezer_time else None,
        "freezer_safe_until_hhmm": _fmt(freezer_until) if freezer_time else None,
        "freezer_status": "ok" if freezer_ok else "check_ice_crystals_or_discard",
        "rule_ids": [fridge.id, freezer.id],
        "sources": [fridge.source(), freezer.source()],
        "assumptions": assumptions,
        "unverified_rules_used": fridge.unverified or freezer.unverified,
    }


_DAYS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
}


def _day(when: datetime, now: datetime, lang: str) -> str:
    delta = (when.date() - now.date()).days
    if delta == 0:
        return "today" if lang == "en" else "hoy"
    if delta == 1:
        return "tomorrow" if lang == "en" else "mañana"
    return _DAYS[lang][when.weekday()]


def outage_summary(now, fridge_until, freezer_until, fridge_ok, freezer_ok, freezer_hours) -> dict:
    """Plain-language verdict built in code, so the model only has to relay it (es/en)."""
    out: dict = {}
    for lang in ("en", "es"):
        fh, zh = _fmt(fridge_until), _fmt(freezer_until)
        zday = _day(freezer_until, now, lang)
        if lang == "en":
            if fridge_ok:
                fridge = f"Fridge: keep the door closed; food stays within the rule until {fh}."
            elif now >= fridge_until:
                fridge = (
                    f"Fridge: the 4-hour limit ended at {fh}. Throw away perishable food from "
                    "the fridge, or check it with a food thermometer."
                )
            else:
                fridge = (
                    "Fridge: the door was opened (or we don't know), so the 4-hour rule may not "
                    "hold. Check with a food thermometer; if you can't, treat perishable food as unsafe."
                )
            freezer = (
                f"Freezer: keep it closed; food stays within the {freezer_hours}-hour rule until {zday} {zh}."
                if freezer_ok
                else "Freezer: check for ice crystals; if the food has none, throw it away."
            )
        else:
            if fridge_ok:
                fridge = (
                    f"Refri: no abras la puerta; la comida sigue dentro de la regla hasta las {fh}."
                )
            elif now >= fridge_until:
                fridge = (
                    f"Refri: el límite de 4 horas terminó a las {fh}. Desecha la comida perecedera "
                    "del refri o revísala con un termómetro de cocina."
                )
            else:
                fridge = (
                    "Refri: la puerta se abrió (o no sabemos), así que la regla de 4 horas puede no "
                    "cumplirse. Revisa con un termómetro de cocina; si no puedes, trata la comida "
                    "perecedera como insegura."
                )
            freezer = (
                f"Congelador: no lo abras; la comida sigue dentro de la regla de {freezer_hours} horas "
                f"hasta {zday if zday in ('hoy', 'mañana') else 'el ' + zday} a las {zh}."
                if freezer_ok
                else "Congelador: revisa si la comida aún tiene cristales de hielo; si no, deséchala."
            )
        out[lang] = f"{fridge} {freezer}"
    return out


# ---------------------------------------------------------------------------
# 2. Meal planning and 5. shelter / community kitchen batches
# ---------------------------------------------------------------------------


def _room_limit(
    hourly_temps: HourlyTemps | None, start: datetime, end: datetime
) -> tuple[int, list[Rule], str]:
    hot = get_rule("FDA_HOT_1H")
    base = get_rule("WHO_COOKED_2H")
    max_t = _max_temp_between(hourly_temps, start, end)
    if max_t is None:
        return hot.limit_minutes, [hot], "No forecast: assumed hot day (> 32 °C)."
    if max_t > hot.hot_threshold_c:
        return hot.limit_minutes, [hot], f"Forecast reaches {max_t:.1f} °C."
    return base.limit_minutes, [base, get_rule("FDA_2H")], f"Forecast max {max_t:.1f} °C."


def plan_shelter_batches(
    people: int,
    service_windows: list[tuple[datetime, datetime]],
    dishes: list[str],
    can_hot_hold: bool,
    hourly_temps: HourlyTemps | None = None,
    cook_minutes: int = 60,
    audience: str = "general",
) -> dict:
    """Staggered batches so nothing is served outside its safe window.

    - With hot holding (>= 60 °C): one batch per service window, kept hot, leftovers discarded
      at the end of service.
    - Without it: split each service window into batches no longer than the room-temperature
      limit; each batch is ready at its start and discarded at ready + limit.
    """
    if people <= 0:
        raise ValueError("people must be > 0")
    batches: list[dict] = []
    used: list[Rule] = []
    assumptions: list[str] = []
    windows_info: list[dict] = []

    for w_start, w_end in service_windows:
        if w_end <= w_start:
            raise ValueError("service window end must be after start")
        window_min = int((w_end - w_start).total_seconds() // 60)
        windows_info.append({"start_hhmm": _fmt(w_start), "end_hhmm": _fmt(w_end),
                             "service_minutes": window_min})  # fmt: skip

        if can_hot_hold:
            hold = get_rule("WHO_HOT_HOLD_60C")
            used.append(hold)
            batches.append(
                {
                    "start_cooking": (w_start - timedelta(minutes=cook_minutes)).isoformat(),
                    "ready_at": w_start.isoformat(),
                    "ready_hhmm": _fmt(w_start),
                    "portions": people,
                    "keep_above_c": hold.hot_hold_min_c,
                    "discard_at": w_end.isoformat(),
                    "discard_hhmm": _fmt(w_end),
                    "dishes": dishes,
                }
            )
            assumptions.append(
                "Food must stay above 60 °C the whole service; if it cools, the room-temperature clock starts."
            )
            continue

        limit, rules, note = _room_limit(hourly_temps, w_start, w_end)
        if audience in CHILD_AUDIENCES:
            rules = [*rules, get_rule("POLICY_CHILD_STRICT")]
            limit = min(limit, get_rule("POLICY_CHILD_STRICT").limit_minutes)
        used += rules
        assumptions.append(note)
        n = max(1, math.ceil(window_min / limit))
        per_batch = math.ceil(people / n)
        for i in range(n):
            ready = w_start + timedelta(minutes=i * limit)
            discard = ready + timedelta(minutes=limit)
            batches.append(
                {
                    "start_cooking": (ready - timedelta(minutes=cook_minutes)).isoformat(),
                    "ready_at": ready.isoformat(),
                    "ready_hhmm": _fmt(ready),
                    "portions": per_batch,
                    "discard_at": discard.isoformat(),
                    "discard_hhmm": _fmt(discard),
                    "dishes": dishes,
                }
            )

    unique = list(dict.fromkeys(used))
    return {
        "people": people,
        "service_windows": windows_info,
        "batches": batches,
        "rule_ids": [r.id for r in unique],
        "sources": [r.source() for r in unique],
        "assumptions": list(dict.fromkeys(assumptions)),
        "unverified_rules_used": any(r.unverified for r in unique),
    }


def plan_meals(
    people: int,
    meal_times: list[datetime],
    dishes: list[str],
    hourly_temps: HourlyTemps | None = None,
    cook_minutes: int = 60,
    audience: str = "general",
) -> dict:
    """Household plan: cook for each meal right before it, only the portions needed."""
    plans = []
    used: list[Rule] = []
    assumptions: list[str] = []
    for meal in meal_times:
        limit, rules, note = _room_limit(hourly_temps, meal, meal + timedelta(minutes=120))
        if audience in CHILD_AUDIENCES:
            strict = get_rule("POLICY_CHILD_STRICT")
            rules = [*rules, strict]
            limit = min(limit, strict.limit_minutes)
        used += rules
        assumptions.append(note)
        plans.append(
            {
                "start_cooking": (meal - timedelta(minutes=cook_minutes)).isoformat(),
                "start_cooking_hhmm": _fmt(meal - timedelta(minutes=cook_minutes)),
                "meal_at": meal.isoformat(),
                "meal_hhmm": _fmt(meal),
                "portions": people,
                "eat_by": (meal + timedelta(minutes=limit)).isoformat(),
                "eat_by_hhmm": _fmt(meal + timedelta(minutes=limit)),
                "dishes": dishes,
            }
        )
    unique = list(dict.fromkeys(used))
    return {
        "meals": plans,
        "advice": "Cook only what will be eaten at this meal; do not keep leftovers at room temperature.",
        "rule_ids": [r.id for r in unique],
        "sources": [r.source() for r in unique],
        "assumptions": list(dict.fromkeys(assumptions)),
        "unverified_rules_used": any(r.unverified for r in unique),
    }


# ---------------------------------------------------------------------------
# 6. Danger signs -> escalation (no diagnosis, no doses)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_danger_signs() -> dict:
    return yaml.safe_load((RULES_DIR / "danger_signs.yaml").read_text(encoding="utf-8"))


def check_danger_signs(answers: dict[str, bool | None], country: str | None = None) -> dict:
    """Escalate if ANY sign is present. Unknown answers count as 'maybe' -> escalate too."""
    cfg = load_danger_signs()
    known_ids = [s["id"] for s in cfg["signs"]]
    present = [sid for sid in known_ids if answers.get(sid) is True]
    unknown = [sid for sid in known_ids if answers.get(sid) is None]
    escalate = bool(present) or bool(unknown)
    number = cfg["emergency_numbers"].get((country or "").upper())
    if escalate:
        message_id = "ESCALATE_EMERGENCY" if number else "ESCALATE_LOCAL_EMERGENCY"
    else:
        message_id = "NO_SIGNS_KEEP_DRINKING_SEEK_CARE_IF_WORSE"
    return {
        "escalate": escalate,
        "message_id": message_id,
        "signs_present": present,
        "signs_unknown": unknown,
        "emergency_number": number,
        "source": {
            "source_name": cfg["source_name"],
            "source_url": cfg["source_url"],
            "verified_on": cfg["verified_on"],
        },
    }
