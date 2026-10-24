"""AT-INT-08: zero baseline denominators yield explicit 0 values listed as unavailable (§16A.9–§16A.12)."""

from decimal import Decimal

from mulenetx.interventions.metrics import compute
from mulenetx.interventions.pool import Spec, rank_pool
from mulenetx.interventions.residual import residual
from tests.interventionutil import baseline


def test_AT_INT_08_empty_baseline() -> None:
    b = baseline([("A", "B", "10")], {"A": "0.9", "B": "0.1"}, ["A", "B"])  # B not suspicious → P empty
    assert b.paths == [] and rank_pool(b, 5000) == []
    m = compute(b, Spec("ACCOUNT_REMOVAL", ("A",)), residual(b, Spec("ACCOUNT_REMOVAL", ("A",))))
    assert m.unavailable == ["flow_disruption", "path_disruption", "connectivity_disruption", "risk_reduction"]
    for name in (
        "flow_disruption_percentage",
        "normalized_path_disruption",
        "normalized_connectivity_disruption",
        "normalized_risk_reduction",
        "residual_network_risk",
    ):
        assert getattr(m, name) == 0


def test_AT_INT_08_zero_flow_and_zero_mass() -> None:
    # zero-amount transfers between accounts scored 0 under a 0 threshold: paths exist, flow and mass are 0
    b = baseline([("A", "B", "0"), ("B", "C", "0")], {"A": "0", "B": "0", "C": "0"}, ["A"], threshold="0")
    assert len(b.paths) == 2 and b.suspicious_flow == 0 and b.risk_mass == 0
    spec = Spec("ACCOUNT_REMOVAL", ("C",))
    m = compute(b, spec, residual(b, spec))
    assert m.unavailable == ["flow_disruption", "risk_reduction"]
    assert m.flow_disruption == 0 and m.normalized_risk_reduction == 0
    assert m.normalized_path_disruption == Decimal("0.5000000")  # A→B→C removed, A→B kept
