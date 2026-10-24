"""AT-RISK-01: fixed component values give the exact formula result to 7 dp."""

from decimal import Decimal

from mulenetx.risk.compose import Components, compose
from tests.riskutil import THRESHOLDS, WEIGHTS


def test_AT_RISK_01_exact_formula() -> None:
    c = Components(Decimal("0.7123457"), Decimal("0.3333333"), True, Decimal("0.6666667"), True, Decimal("0.8"))
    r = compose(c, Decimal("0.2381000"), WEIGHTS, THRESHOLDS)
    # 0.35617285 + 0.06666666 + 0.100000005 + 0.04 = 0.562839515 → 0.5628395 (half-even, 7 dp)
    assert format(r.pre_propagation_score, "f") == "0.5628395"
    # 0.5628395 + 0.10·0.2381000 = 0.5866495
    assert format(r.final_score, "f") == "0.5866495"
    assert r.risk_tier == "HIGH"
