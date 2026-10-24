"""AT-EVAL-02: network identification, suspicious-flow coverage, network-risk ranking and intervention
effectiveness (rank-1 RANK candidate vs a degree-ranked baseline evaluated through the intervention code path)."""

import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from tests.apiutil import _Req
from tests.evalutil import evaluate, metric, seed_with_ring
from tests.ingestutil import run_worker

pytestmark = pytest.mark.integration


def test_AT_EVAL_02_network_metrics(app, client, users) -> None:
    admin = users("ADMIN")
    seed_with_ring(app, client, admin, "e2")
    first = evaluate(app, client, admin)
    matches = metric(first, "RING", "mean_matched_jaccard")["details"]["matches"]
    assert matches, "the injected cluster is matched to a reference ring"
    rings = {
        r["ring_id"]: r
        for r in client.get("/api/v1/rings", params={"page_size": 100}, headers=admin.headers).json()["items"]
    }
    matched_potential = [
        m["analytical_ring_id"]
        for m in matches
        if rings[m["analytical_ring_id"]]["candidate_class"] == "POTENTIAL_FRAUD_RING_CANDIDATE"
    ]
    assert matched_potential
    rank1 = metric(first, "NETWORK", "intervention_effectiveness_rank1")
    assert rank1["state"] == "UNAVAILABLE" and "RANK scenario" in rank1["details"]["reason"]

    for rid in matched_potential:
        assert (
            client.post(
                f"/api/v1/rings/{rid}/interventions/simulate", json={"mode": "RANK"}, headers=admin.headers
            ).status_code
            == 202
        )
    run_worker(app, timeout=600)
    s = evaluate(app, client, admin)

    # independent recomputation of the network identification metrics
    rt = get_services(_Req(app)).runtime
    window = s["configuration"]["test_window"]
    with rt.engine.connect() as conn:
        identified = {
            r[0]
            for r in conn.execute(
                text(
                    "SELECT m.account_id FROM potential_fraud_ring_candidates c JOIN community_memberships m "
                    "ON m.analytics_run_id = c.analytics_run_id AND m.community_id = c.community_id "
                    "WHERE c.scoring_run_id = :s"
                ),
                {"s": s["scoring_run_id"]},
            )
        }
        positives = conn.execute(
            text(
                "SELECT source_account_id AS u, destination_account_id AS v, amount FROM transactions "
                'WHERE dataset_id = :d AND fraud_label AND "timestamp" > :lo AND "timestamp" <= :hi'
            ),
            {"d": s["dataset_id"], "lo": window["after"], "hi": window["until"]},
        ).all()
    covered = sum(float(p.amount) for p in positives if p.u in identified and p.v in identified)
    assert metric(s, "NETWORK", "suspicious_flow_coverage")["value"] == pytest.approx(
        covered / sum(float(p.amount) for p in positives)
    )
    assert metric(s, "NETWORK", "network_precision")["sample_count"] == len(identified)
    assert metric(s, "NETWORK", "network_risk_ranking")["state"] == "AVAILABLE"

    rank1 = metric(s, "NETWORK", "intervention_effectiveness_rank1")
    degree = metric(s, "NETWORK", "intervention_effectiveness_degree_baseline")
    assert rank1["state"] == "AVAILABLE" and rank1["details"]["simulated"] is True
    assert "never a measure of real-world enforcement" in rank1["details"]["statement"]
    ring_entry = rank1["details"]["rings"][0]
    assert 0 <= ring_entry["rank1_flow_disruption_percentage"] <= 1
    assert ring_entry["degree_baseline"]["account_id"]
    # both are reported side by side; the rank-1 candidate maximizes the intervention score, not flow disruption
    # alone, so neither is required to dominate the other
    assert degree["details"]["distribution"]["count"] == (1 if degree["state"] == "AVAILABLE" else 0)
    for d in (rank1["details"]["distribution"], degree["details"]["distribution"]):
        assert d["count"] == 0 or 0 <= d["min"] <= d["mean"] <= d["max"] <= 1
