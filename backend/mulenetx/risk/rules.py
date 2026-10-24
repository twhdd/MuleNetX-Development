"""Rule evaluation (SRS §12.5): a rule whose input is unavailable does not fire; rule_signal_score is the
maximum contribution among fired rules (0 if none), capped at 1.0. Priority only orders explanations."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from mulenetx.core.decimal import ONE, ZERO, D, round7
from mulenetx.features.encoding import State

OPS = {">=": lambda a, b: a >= b, ">": lambda a, b: a > b}


@dataclass(frozen=True)
class RuleResult:
    score: Decimal
    fired: list[dict[str, Any]]
    available: bool


def evaluate(
    rules: list[dict[str, Any]],
    values: Mapping[str, float],
    states: Mapping[str, int],
    quantities: Mapping[str, float | None],
) -> RuleResult:
    fired: list[dict[str, Any]] = []
    any_evaluable = False
    for rule in rules:
        ok = True
        evaluable = True
        for cond in rule["conditions"]:
            if "feature" in cond:
                fid = cond["feature"]
                if states.get(fid) in (State.UNAVAILABLE, State.NOT_APPLICABLE) or math.isnan(
                    values.get(fid, math.nan)
                ):
                    evaluable = False
                    break
                actual = D(values[fid])
            else:
                q = quantities.get(cond["quantity"])
                if q is None:
                    evaluable = False
                    break
                actual = D(q)
            if not OPS[cond["op"]](actual, D(cond["value"])):
                ok = False
        if not evaluable:
            continue
        any_evaluable = True
        if ok:
            fired.append({"rule_id": rule["id"], "contribution": rule["contribution"], "priority": rule["priority"]})
    fired.sort(key=lambda r: (-int(r["priority"]), r["rule_id"]))
    score = max((D(r["contribution"]) for r in fired), default=ZERO)
    return RuleResult(round7(min(score, ONE)), fired, any_evaluable)
