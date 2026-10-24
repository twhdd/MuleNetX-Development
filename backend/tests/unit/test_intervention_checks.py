"""SRS §27.10 checks 1–3 and 6 on small graphs, and property tests: residual ⊆ baseline; residual risk is monotone
in the target set."""

from hypothesis import given, settings
from hypothesis import strategies as st

from mulenetx.flow.analytic_paths import Budget, enumerate_ring_scope
from mulenetx.interventions.baseline import build
from mulenetx.interventions.metrics import compute
from mulenetx.interventions.pool import Spec
from mulenetx.interventions.residual import residual
from tests.flowutil import context, projection_from_edges
from tests.interventionutil import baseline, label, rank


def test_peripheral_account_disrupts_less_than_sole_intermediary() -> None:
    # S → M → T1, S → M → T2, and a peripheral suspicious P with one path P → T1
    edges = [("S", "M", "10"), ("M", "T1", "10"), ("M", "T2", "10"), ("P", "T1", "1")]
    b = baseline(edges, {"S": "0.9", "T1": "0.9", "T2": "0.9", "P": "0.6", "M": "0.1"}, ["S", "M", "T1", "T2", "P"])
    results = {label(r): r for r in rank(b)}
    sole = results["INTERMEDIARY_REMOVAL M"]
    peripheral = results["ACCOUNT_REMOVAL P"]
    assert sole.metrics.flow_disruption_percentage > peripheral.metrics.flow_disruption_percentage
    assert sole.rank_position < peripheral.rank_position


def test_bridge_disconnects_expected_paths() -> None:
    # two clusters {A, B} → X → {C, D} joined only by X
    edges = [("A", "X", "5"), ("B", "X", "5"), ("X", "C", "5"), ("X", "D", "5")]
    b = baseline(edges, {"A": "0.9", "B": "0.9", "C": "0.9", "D": "0.9", "X": "0.1"}, ["A", "B", "C", "D", "X"])
    r = residual(b, Spec("INTERMEDIARY_REMOVAL", ("X",)))
    assert r.residual == [] and {p.pair for p in r.affected} == {("A", "C"), ("A", "D"), ("B", "C"), ("B", "D")}


def test_redundant_paths_survive_one_intermediary() -> None:
    edges = [("S", "M1", "5"), ("S", "M2", "5"), ("M1", "T", "5"), ("M2", "T", "5")]
    b = baseline(edges, {"S": "0.9", "T": "0.9"}, ["S", "T"])
    r = residual(b, Spec("INTERMEDIARY_REMOVAL", ("M1",)))
    assert [p.accounts for p in r.residual] == [("S", "M2", "T")]
    assert [p.accounts for p in r.alternative] == [("S", "M2", "T")]
    m = compute(b, Spec("INTERMEDIARY_REMOVAL", ("M1",)), r)
    assert m.normalized_connectivity_disruption == 0  # S can still reach T


def test_residual_equals_fresh_enumeration_on_the_hypothetical_graph() -> None:
    edges = [("A", "B", "5"), ("B", "C", "5"), ("A", "D", "5"), ("D", "C", "5"), ("C", "E", "5"), ("E", "A", "5")]
    scores = {"A": "0.9", "B": "0.2", "C": "0.8", "D": "0.6", "E": "0.1"}
    members = ["A", "C"]
    b = baseline(edges, scores, members)
    assert not b.truncated
    for removed in ("B", "D", "E"):
        r = residual(b, Spec("ACCOUNT_REMOVAL", (removed,)))
        fresh_proj = projection_from_edges([e for e in edges if removed not in e[:2]])
        fresh = enumerate_ring_scope(fresh_proj, members, context(scores), Budget())
        assert sorted(p.accounts for p in r.residual) == sorted(fresh.qualifying_paths), removed


NODES = ["N0", "N1", "N2", "N3", "N4", "N5"]


@settings(max_examples=60, deadline=None)
@given(
    edges=st.lists(st.tuples(st.sampled_from(NODES), st.sampled_from(NODES)), min_size=1, max_size=12),
    suspicious=st.sets(st.sampled_from(NODES), min_size=2),
    x=st.sets(st.sampled_from(NODES), max_size=2),
    y_extra=st.sets(st.sampled_from(NODES), max_size=1),
)
def test_residual_subset_and_monotone_risk(edges, suspicious, x, y_extra) -> None:  # type: ignore[no-untyped-def]
    edge_rows = [(u, v, "1") for u, v in dict.fromkeys(edges) if u != v]
    if not edge_rows:
        return
    scores = {n: ("0.9" if n in suspicious else "0.1") for n in NODES}
    proj = projection_from_edges(edge_rows)
    run = context(scores)
    b = build(proj, run, enumerate_ring_scope(proj, NODES[:3], run, Budget()))
    small = Spec("ACCOUNT_SET_REMOVAL", tuple(sorted(x)))
    big = Spec("ACCOUNT_SET_REMOVAL", tuple(sorted(x | y_extra)))
    rs, rb = residual(b, small), residual(b, big)
    baseline_ids = {p.path_id for p in b.paths}
    assert {p.path_id for p in rs.residual} <= baseline_ids
    assert {p.path_id for p in rb.residual} <= {p.path_id for p in rs.residual}
    if b.paths:
        ms, mb = compute(b, small, rs), compute(b, big, rb)
        assert mb.residual_risk_mass <= ms.residual_risk_mass
        assert mb.normalized_risk_reduction >= ms.normalized_risk_reduction
