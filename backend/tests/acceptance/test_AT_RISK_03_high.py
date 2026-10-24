"""AT-RISK-03: a final score of 0.50 is tier HIGH."""

from decimal import Decimal

from mulenetx.risk.compose import Components, compose
from mulenetx.risk.tiers import tier
from tests.riskutil import THRESHOLDS, WEIGHTS


def test_AT_RISK_03_tier_HIGH() -> None:
    assert tier(Decimal("0.50"), THRESHOLDS) == "HIGH"
    assert tier(Decimal("0.50") - Decimal("0.0000001"), THRESHOLDS) != "HIGH"


def test_AT_RISK_03_via_composition() -> None:
    # ml alone: final = 0.5 × ml; ml = 2 × score (≤ 1), remainder through the graph component
    target = Decimal("0.50")
    ml = min(target * 2, Decimal(1))
    graph = (target - ml / 2) / Decimal("0.2")
    r = compose(Components(ml, graph, True, Decimal(0), True, Decimal(0)), Decimal(0), WEIGHTS, THRESHOLDS)
    assert r.final_score == target and r.risk_tier == "HIGH"
