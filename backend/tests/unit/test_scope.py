"""Ring scope, eligible and qualifying paths, flows (SRS §3.5) on hand-built projections."""

from decimal import Decimal

import pytest

from mulenetx.flow.analytic_paths import Budget, enumerate_ring_scope
from tests.flowutil import context, projection_from_edges

BUDGET = Budget(max_depth=5, max_paths=10_000, max_expansions=1_000_000)


def test_chain_through_non_suspicious_middle() -> None:
    # A(s) → B → C(s) → D ; ring {A}
    proj = projection_from_edges([("A", "B", "100"), ("B", "C", "90"), ("C", "D", "5")])
    run = context({"A": "0.9", "B": "0.1", "C": "0.7", "D": "0.1"})
    r = enumerate_ring_scope(proj, ["A"], run, BUDGET)
    assert r.scope == {"A", "B", "C"}  # D lies on no qualifying path
    assert r.eligible_paths == [("A", "B"), ("A", "B", "C")]
    assert r.qualifying_paths == [("A", "B", "C")]
    assert r.eligible_flow == Decimal("190")
    assert r.suspicious_flow == Decimal("190")  # A→B (A suspicious) and B→C (C suspicious)
    assert r.suspicious_accounts == {"A", "C"}
    assert r.reachable_pairs == {("A", "C")}
    assert not r.truncated


def test_backward_paths_into_the_ring_and_dedup() -> None:
    # P(s) → Q → R(s, ring member); R → P closes a cycle; ring {R}
    proj = projection_from_edges([("P", "Q", "10"), ("Q", "R", "10"), ("R", "P", "3")])
    run = context({"P": "0.6", "Q": "0.2", "R": "0.6"})
    r = enumerate_ring_scope(proj, ["R"], run, BUDGET)
    assert set(r.qualifying_paths) == {("P", "Q", "R"), ("R", "P")}
    assert r.reachable_pairs == {("P", "R"), ("R", "P")}
    assert len(r.eligible_paths) == len(set(r.eligible_paths))  # forward and backward finds deduplicated
    for p in r.eligible_paths:
        assert len(p) == len(set(p))  # simple paths only


def test_suspicious_flow_excludes_non_suspicious_hops() -> None:
    # A(s) → X → Y → B(s): the X→Y transaction touches no suspicious account
    proj = projection_from_edges([("A", "X", "50"), ("X", "Y", "40"), ("Y", "B", "30")])
    run = context({"A": "0.9", "X": "0.1", "Y": "0.1", "B": "0.9"})
    r = enumerate_ring_scope(proj, ["A"], run, BUDGET)
    assert r.qualifying_paths == [("A", "X", "Y", "B")]
    assert r.suspicious_flow == Decimal("80")
    assert r.eligible_flow == Decimal("120")


def test_depth_bound() -> None:
    chain = [(f"N{i}", f"N{i + 1}", "1") for i in range(7)]
    proj = projection_from_edges(chain)
    run = context({f"N{i}": "0.9" for i in range(8)})
    r = enumerate_ring_scope(proj, ["N0"], run, Budget(max_depth=5))
    assert max(len(p) - 1 for p in r.eligible_paths) == 5
    assert ("N0", "N1", "N2", "N3", "N4", "N5", "N6") not in r.eligible_paths


def test_expansion_counter_truncates_deterministically() -> None:
    proj = projection_from_edges([("A", f"B{i}", "1") for i in range(10)])
    run = context({"A": "0.9", **{f"B{i}": "0.9" for i in range(10)}})
    r = enumerate_ring_scope(proj, ["A"], run, Budget(max_expansions=4))
    assert r.truncated
    assert r.qualifying_paths == [("A", "B0"), ("A", "B1"), ("A", "B2"), ("A", "B3")]


def test_mixing_contexts_is_refused() -> None:
    import uuid

    proj = projection_from_edges([("A", "B", "1")])
    run = context({"A": "0.9"}, snapshot=uuid.UUID("00000000-0000-5000-8000-0000000000dd"))
    with pytest.raises(ValueError, match="mixing contexts"):
        enumerate_ring_scope(proj, ["A"], run, BUDGET)
