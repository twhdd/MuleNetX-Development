"""AT-GRAPH-01: building canonical A→B→C gives matching IDs, topology, counts and digest; no labels in Neo4j."""

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import GraphSnapshot
from mulenetx.graph.validate import digest
from tests.apiutil import _Req
from tests.ingestutil import fixture_csv, run_worker, upload

pytestmark = pytest.mark.integration


def test_AT_GRAPH_01_build_matches_canonical(app, client, users) -> None:
    admin = users("ADMIN")
    body = upload(client, admin, fixture_csv("abc_chain"), name="graph abc").json()
    run_worker(app)
    key = body["dataset_key"]
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        snap = db.execute(select(GraphSnapshot).where(GraphSnapshot.purpose == "OPERATIONAL")).scalar_one()
    assert snap.status == "READY" and snap.purpose == "OPERATIONAL"
    assert snap.node_count == 5 and snap.edge_count == 2 and snap.source_record_count == 2
    assert snap.data_cutoff.isoformat() == "2020-01-01T02:00:00+00:00"
    assert snap.validation_digest == digest([f"{key}:0000000001", f"{key}:0000000002"])

    sid = str(snap.graph_snapshot_id)
    accounts = rt.graph.run("MATCH (a:Account {snapshot_id: $sid}) RETURN a ORDER BY a.account_id", {"sid": sid})
    assert [a["a"]["account_id"] for a in accounts] == [f"{key}:CA", f"{key}:CB", f"{key}:CC"]
    assert all(a["a"]["snapshot_key"] == f"{sid}:{a['a']['account_id']}" for a in accounts)
    edges = rt.graph.run(
        "MATCH (a:Account {snapshot_id:$sid})-[r:TRANSFERRED_TO]->(b) RETURN a.account_id AS s, b.account_id AS d, "
        "r.tx_count AS n, r.total_amount AS amt, r.snapshot_id AS rs ORDER BY s",
        {"sid": sid},
    )
    assert [(e["s"], e["d"], e["n"], e["amt"], e["rs"]) for e in edges] == [
        (f"{key}:CA", f"{key}:CB", 1, 100.0, sid),
        (f"{key}:CB", f"{key}:CC", 1, 50.0, sid),
    ]
    evidence = rt.graph.run(
        "MATCH (s:Account)-[:SENDS]->(t:Transaction {snapshot_id:$sid})-[:RECEIVED_BY]->(d:Account) "
        "RETURN t.transaction_id AS t, s.account_id AS s, d.account_id AS d ORDER BY t",
        {"sid": sid},
    )
    assert [(e["t"], e["s"], e["d"]) for e in evidence] == [
        (f"{key}:0000000001", f"{key}:CA", f"{key}:CB"),
        (f"{key}:0000000002", f"{key}:CB", f"{key}:CC"),
    ]
    leaked = rt.graph.run(
        "MATCH (n) WHERE n.fraud_label IS NOT NULL OR n.isFraud IS NOT NULL OR n.isFlaggedFraud IS NOT NULL "
        "RETURN count(n) AS n"
    )
    assert leaked[0]["n"] == 0
    rels = rt.graph.run("MATCH ()-[r]->() WHERE r.fraud_label IS NOT NULL RETURN count(r) AS n")
    assert rels[0]["n"] == 0
