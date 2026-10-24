"""AT-INT-01 (§27.10 check 5): a simulation leaves PostgreSQL canonical and analytical state and the Neo4j graph
unchanged (row counts and digests before and after); only the two intervention tables gain rows."""

import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from tests.apiutil import _Req
from tests.scenarioutil import complete, potential_ring, simulate

pytestmark = pytest.mark.integration

TABLES = (
    "accounts",
    "transactions",
    "risk_assessments",
    "account_feature_values",
    "account_graph_metrics",
    "communities",
    "community_memberships",
    "potential_fraud_ring_candidates",
    "ring_memberships",
    "ring_feature_sets",
    "ring_risk_assessments",
    "temporal_motifs",
    "cases",
    "case_subjects",
    "findings",
    "graph_snapshots",
    "scoring_runs",
    "analytics_runs",
    "active_context",
    "users",
)


def _state(rt):  # type: ignore[no-untyped-def]
    with rt.engine.connect() as conn:
        counts = {t: conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in TABLES}  # noqa: S608
        digest = conn.execute(
            text(
                "SELECT md5(string_agg(account_id || ':' || coalesce(risk_score::text, '') || ':' || "
                "coalesce(risk_tier, ''), ',' ORDER BY account_id)) FROM accounts"
            )
        ).scalar_one()
        tx_digest = conn.execute(
            text(
                "SELECT md5(string_agg(transaction_id || ':' || amount::text, ',' ORDER BY transaction_id)) "
                "FROM transactions"
            )
        ).scalar_one()
        context = conn.execute(text("SELECT * FROM active_context")).one()._asdict()
    graph = rt.graph.run(
        "MATCH (n) WITH count(n) AS nodes MATCH ()-[r]->() "
        "RETURN nodes, count(r) AS rels, sum(coalesce(r.total_amount_micros, 0)) AS micros"
    )
    return counts, digest, tx_digest, context, graph


def test_AT_INT_01_no_canonical_mutation(app, client, users) -> None:
    admin = users("ADMIN")
    ring = potential_ring(app, client, admin, "i1")
    rt = get_services(_Req(app)).runtime
    inv = users("INVESTIGATOR")
    before = _state(rt)
    resp = simulate(client, inv, ring["ring_id"], {"mode": "RANK"})
    assert resp.status_code == 202, resp.text
    scenario = complete(app, client, inv, resp.json()["scenario_id"])
    assert scenario["status"] == "COMPLETED", scenario
    after = _state(rt)
    assert after[0]["users"] == before[0]["users"]
    assert after == before
    with rt.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM intervention_scenarios")).scalar_one() == 1
        assert conn.execute(text("SELECT count(*) FROM intervention_candidates")).scalar_one() > 0
