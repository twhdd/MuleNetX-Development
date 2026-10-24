"""AT-PROP-01: a source with pre-propagation score 0.8 at distance 1 contributes 0.40."""

from decimal import Decimal

from mulenetx.propagation.bfs import propagate, propagated_risk, undirected_adjacency


def test_AT_PROP_01_contribution() -> None:
    adj = undirected_adjacency([("S", "X"), ("X", "Y"), ("Y", "Z"), ("Z", "W")])
    out = propagate(adj, {"S": Decimal("0.8"), "X": Decimal("0.1")}, Decimal("0.50"), 3, Decimal("0.50"), 5)
    assert propagated_risk(out["X"]) == Decimal("0.4000000")
    assert out["X"][0].distance == 1 and out["X"][0].decay_value == Decimal("0.5000000")
    assert propagated_risk(out["Y"]) == Decimal("0.2666667")  # 0.8 / 3
    assert propagated_risk(out["Z"]) == Decimal("0.2000000")  # 0.8 / 4
    assert "W" not in out  # beyond maximum_distance 3
    assert "S" not in out  # an account is never its own source


def test_AT_PROP_01_cap_and_source_condition() -> None:
    adj = undirected_adjacency([("S", "X")])
    out = propagate(adj, {"S": Decimal("0.49")}, Decimal("0.50"), 3, Decimal("0.50"), 5)
    assert out == {}  # below the source threshold
    capped = propagate(adj, {"S": Decimal("1.2")}, Decimal("0.50"), 3, Decimal("0.50"), 5)
    assert propagated_risk(capped["X"]) == Decimal("0.5000000")  # safety cap min(s/(1+d), 0.50)
