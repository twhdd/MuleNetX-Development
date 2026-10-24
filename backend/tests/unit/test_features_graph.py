"""Graph and flow features (SRS §10.1 F11–F18, F32, F34) and the risk-derived regime (§10.2)."""

from decimal import Decimal

import pytest

from mulenetx.analytics.projection import PairAggregate, Projection
from mulenetx.features.encoding import State
from mulenetx.features.flow_features import adjacency, bounded_paths, flow_features
from mulenetx.features.graph_features import community_densities, risk_derived
from mulenetx.features.registry import RISK_DERIVED


def _proj(pairs: list[tuple[str, str]]) -> Projection:
    nodes = sorted({x for p in pairs for x in p})
    return Projection(nodes, [PairAggregate(a, b, 1, Decimal(1)) for a, b in sorted(pairs)])


def test_network_density_of_community() -> None:
    proj = _proj([("A", "B"), ("B", "A"), ("B", "C"), ("C", "D")])
    density = community_densities(proj, {"A": "x", "B": "x", "C": "x", "D": "y"})
    assert density == {"x": pytest.approx(2 * 2 / (3 * 2)), "y": 0.0}  # A–B counted once (undirected simple)


def test_bounded_paths_preorder_and_cap() -> None:
    adj = adjacency(_proj([("S", "A"), ("S", "B"), ("A", "C"), ("C", "S"), ("C", "D")]))
    assert bounded_paths(adj, "S", 5, 100) == (4, {"A", "C"})  # S-A, S-A-C, S-A-C-D, S-B; S-A-C-S is not simple
    assert bounded_paths(adj, "S", 5, 2) == (2, {"A"})


def test_bounded_paths_depth_limit() -> None:
    chain = [(f"N{i}", f"N{i + 1}") for i in range(8)]
    adj = adjacency(_proj(chain))
    count, inside = bounded_paths(adj, "N0", 5, 100)
    assert count == 5 and inside == {"N1", "N2", "N3", "N4"}


def test_f32_cap_at_100() -> None:
    fan = [("S", f"X{i:03d}") for i in range(150)]
    out = flow_features(adjacency(_proj(fan)), "S", True, 5, 100)
    assert out["F32"] == (100.0, State.OBSERVED) and out["F34"] == (0.0, State.ZERO)


def test_flow_unavailable_outside_snapshot() -> None:
    out = flow_features({}, "Z", False, 5, 100)
    assert out["F32"][1] == State.UNAVAILABLE and out["F34"][1] == State.UNAVAILABLE


def test_risk_derived_unavailable_and_other_regimes_not_implemented() -> None:
    values = risk_derived("RISK_FEATURES_UNAVAILABLE")
    assert set(values) == set(RISK_DERIVED) and all(s == State.UNAVAILABLE for _, s in values.values())
    with pytest.raises(NotImplementedError):
        risk_derived("PRIOR_RUN")
