"""AT-RISK-05: with the graph signal unavailable, the component is 0 and UNAVAILABLE; coverage is reported."""

import math
from decimal import Decimal

from mulenetx.risk.components import component
from mulenetx.risk.compose import Components, compose
from mulenetx.risk.config import G_SET, NORMALIZATION
from tests.riskutil import THRESHOLDS, WEIGHTS


def test_AT_RISK_05_graph_unavailable() -> None:
    values = dict.fromkeys(G_SET, math.nan)
    states = dict.fromkeys(G_SET, 2)
    g = component(list(G_SET), values, states, NORMALIZATION, {})
    assert g.score == Decimal(0) and g.available is False
    r = compose(
        Components(Decimal("0.6"), g.score, g.available, Decimal("0.4"), True, Decimal(0)),
        Decimal(0),
        WEIGHTS,
        THRESHOLDS,
    )
    assert format(r.final_score, "f") == "0.3600000"
    assert format(r.signal_coverage, "f") == "0.8000000"  # 1 − w_g
    assert format(r.max_attainable_score, "f") == "0.5600000"  # graph at 1 adds 0.20
