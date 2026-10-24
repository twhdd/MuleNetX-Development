"""§28.7 reference rings and one-to-one ring matching."""

from fractions import Fraction

from mulenetx.core import ids
from mulenetx.evaluation.matching import jaccard, match
from mulenetx.evaluation.reference import REFERENCE_CONSTRUCTION_VERSION, reference_rings


def fs(*a: str) -> frozenset[str]:
    return frozenset(a)


def test_reference_rings_are_wcc_with_three_accounts() -> None:
    edges = [("A", "B"), ("C", "B"), ("X", "Y"), ("P", "Q"), ("Q", "R"), ("R", "P")]
    rings = reference_rings(edges)
    assert sorted(sorted(r.members) for r in rings) == [["A", "B", "C"], ["P", "Q", "R"]]  # X–Y has only 2
    for r in rings:
        assert r.ring_id == str(ids.reference_ring_id(REFERENCE_CONSTRUCTION_VERSION, sorted(r.members)))


def test_jaccard_threshold_and_one_to_one() -> None:
    assert jaccard(fs("a", "b"), fs("b", "c")) == Fraction(1, 3)
    analytical = {"a1": fs("p", "q", "r", "s"), "a2": fs("p", "q", "r")}
    reference = {"r1": fs("p", "q", "r")}
    # a2 has J = 1, a1 has J = 3/4: a2 wins; a1 stays unmatched (one-to-one)
    assert [(m.analytical_id, m.reference_id, m.jaccard) for m in match(analytical, reference)] == [("a2", "r1", 1)]
    assert match({"a": fs("x", "y", "z")}, {"r": fs("x", "w", "v", "u")}) == []  # J = 1/6 < 0.5


def test_ties_break_by_reference_then_analytical_id() -> None:
    analytical = {"b": fs("p", "q"), "a": fs("p", "q")}
    reference = {"r2": fs("p", "q"), "r1": fs("p", "q")}
    got = [(m.analytical_id, m.reference_id) for m in match(analytical, reference)]
    assert got == [("a", "r1"), ("b", "r2")]
