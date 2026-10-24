"""AT-INT-06: tied candidates (same score, flow disruption, risk reduction and cost) are ordered by candidate_id."""

from tests.interventionutil import counterexample_baseline, label, rank


def test_AT_INT_06_tie_break() -> None:
    results = {label(r): r for r in rank(counterexample_baseline())}
    for a, b in (("ACCOUNT_REMOVAL A", "EDGE_REMOVAL A>D"), ("ACCOUNT_REMOVAL C", "EDGE_REMOVAL D>C")):
        ra, rb = results[a], results[b]
        assert ra.intervention_score == rb.intervention_score
        assert ra.metrics.flow_disruption_percentage == rb.metrics.flow_disruption_percentage
        assert ra.metrics.normalized_risk_reduction == rb.metrics.normalized_risk_reduction
        assert ra.metrics.intervention_cost == rb.metrics.intervention_cost
        first, second = sorted((ra, rb), key=lambda r: r.candidate_id)
        assert first.rank_position + 1 == second.rank_position
