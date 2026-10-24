"""AT-RISK-04: a final score of 0.75 is tier CRITICAL."""

from decimal import Decimal

from mulenetx.risk.compose import Components, compose
from mulenetx.risk.tiers import tier
from tests.riskutil import THRESHOLDS, WEIGHTS


def test_AT_RISK_04_tier_CRITICAL() -> None:
    assert tier(Decimal("0.75"), THRESHOLDS) == "CRITICAL"
    assert tier(Decimal("0.75") - Decimal("0.0000001"), THRESHOLDS) != "CRITICAL"


def test_AT_RISK_04_via_composition() -> None:
    # ml alone: final = 0.5 × ml; ml = 2 × score (≤ 1), remainder through the graph component
    target = Decimal("0.75")
    ml = min(target * 2, Decimal(1))
    graph = (target - ml / 2) / Decimal("0.2")
    r = compose(Components(ml, graph, True, Decimal(0), True, Decimal(0)), Decimal(0), WEIGHTS, THRESHOLDS)
    assert r.final_score == target and r.risk_tier == "CRITICAL"
