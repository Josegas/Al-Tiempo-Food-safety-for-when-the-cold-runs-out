"""Policy-as-code check for rules/food_rules.yaml.

python scripts/check_rules.py           -> schema check; lists unverified rules (warning)
python scripts/check_rules.py --strict  -> also FAILS if any rule is unverified (release gate)
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REQUIRED = ["id", "description", "source_name", "source_url", "unverified"]
FILE = Path(__file__).resolve().parent.parent / "rules" / "food_rules.yaml"


def main(strict: bool) -> int:
    rules = yaml.safe_load(FILE.read_text(encoding="utf-8"))["rules"]
    errors, unverified, ids = [], [], set()
    for r in rules:
        rid = r.get("id", "<no id>")
        errors += [f"{rid}: missing '{k}'" for k in REQUIRED if k not in r]
        if rid in ids:
            errors.append(f"{rid}: duplicated id")
        ids.add(rid)
        if not str(r.get("source_url", "")).startswith("https://"):
            errors.append(f"{rid}: source_url must be https")
        if "limit_minutes" in r and r["limit_minutes"] is not None:
            if not isinstance(r["limit_minutes"], int) or r["limit_minutes"] <= 0:
                errors.append(f"{rid}: limit_minutes must be a positive integer")
        if r.get("unverified", True):
            unverified.append(rid)
        else:
            if not r.get("verified_on"):
                errors.append(f"{rid}: verified rule needs verified_on")
            if not r.get("verified_text"):
                errors.append(f"{rid}: verified rule needs verified_text (verbatim quote)")
        if r.get("kind", "official") not in ("official", "adapted", "policy"):
            errors.append(f"{rid}: kind must be official, adapted or policy")
        if r.get("kind") == "adapted" and not r.get("adaptation"):
            errors.append(f"{rid}: adapted rule must explain its adaptation")

    for e in errors:
        print(f"::error file=rules/food_rules.yaml::{e}")
    for rid in unverified:
        level = "error" if strict else "warning"
        print(f"::{level} file=rules/food_rules.yaml::{rid} is not verified on its official source")
    print(
        f"{len(rules)} rules, {len(rules) - len(unverified)} verified, {len(unverified)} unverified"
    )
    return 1 if errors or (strict and unverified) else 0


if __name__ == "__main__":
    sys.exit(main("--strict" in sys.argv))
