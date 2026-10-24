"""AT-RING-03: the ring features of §9A.2 on the ring_basic fixture: exact values, availability, truncation."""

from mulenetx.flow.analytic_paths import Budget
from mulenetx.rings.service import intelligence
from tests.ringutil import inputs, load

EXP = load()["expected_ring"]


def test_AT_RING_03_features_exact() -> None:
    ctx = inputs()
    f = intelligence(ctx, ctx.communities["c-ring"]).features
    assert {k: format(v, "f") for k, v in f.values.items()} == EXP["features"]
    assert all(a == "AVAILABLE" for a in f.availability.values())
    assert len(f.scope.eligible_paths) == EXP["eligible_path_count"]
    assert len(f.scope.qualifying_paths) == EXP["qualifying_path_count"]
    assert f.paths_truncated is EXP["paths_truncated"]
    assert sorted(f.scope.scope) == EXP["scope"]
    assert format(f.scope.suspicious_flow, "f") == EXP["suspicious_flow"]
    assert format(f.scope.eligible_flow, "f") == EXP["eligible_flow"]


def test_AT_RING_03_truncation_state() -> None:
    ctx = inputs(Budget(max_paths=4))
    f = intelligence(ctx, ctx.communities["c-ring"]).features
    assert f.paths_truncated is True
    assert f.availability["MFC"] == f.availability["SPD"] == "LOWER_BOUND_TRUNCATED"
    assert len(f.scope.eligible_paths) <= 4


def test_AT_RING_03_zero_denominators_are_unavailable() -> None:
    ctx = inputs()
    f = intelligence(ctx, ["Q1", "Q3"]).features  # no constituent transactions between Q1 and Q3
    assert f.values["RSD"] == 0 and f.availability["RSD"] == "UNAVAILABLE"
    assert f.availability["TC"] == "UNAVAILABLE" and f.availability["SPD"] == "UNAVAILABLE"
