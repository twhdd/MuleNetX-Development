"""A Neo4j/PostgreSQL disagreement fails the snapshot with GRAPH_VALIDATION_MISMATCH (SRS §6.8.4)."""

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import ActiveContext, GraphSnapshot
from mulenetx.graph import service as graph_service
from tests.apiutil import _Req
from tests.ingestutil import fixture_csv, run_worker, upload

pytestmark = pytest.mark.integration


def test_validation_mismatch_fails_snapshot(app, client, users, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = get_services(_Req(app)).runtime
    original = graph_service.validate

    def tampered(graph, snapshot_id, expected):  # type: ignore[no-untyped-def]
        graph.run("MATCH (t:Transaction {snapshot_id:$s}) WITH t LIMIT 1 DETACH DELETE t", {"s": str(snapshot_id)})
        return original(graph, snapshot_id, expected)

    monkeypatch.setattr(graph_service, "validate", tampered)
    admin = users("ADMIN")
    body = upload(client, admin, fixture_csv("abc_chain"), name="mismatch").json()
    run_worker(app)
    run = client.get(f"/api/v1/pipeline-runs/{body['pipeline_run_id']}", headers=admin.headers).json()
    assert run["current_state"] == "FAILED"
    assert run["failure_category"] == "GRAPH_VALIDATION_MISMATCH"
    assert run["resumable_from"] == "GRAPH_BUILDING"
    with rt.session_factory() as db:
        snap = db.execute(select(GraphSnapshot).where(GraphSnapshot.purpose == "OPERATIONAL")).scalar_one()
        assert snap.status == "FAILED" and snap.validation_digest is None
        assert db.execute(select(ActiveContext)).scalar_one().graph_snapshot_id is None


def test_retire_deletes_neo4j_data(app, client, users) -> None:
    from mulenetx.graph.service import GraphService

    rt = get_services(_Req(app)).runtime
    admin = users("ADMIN")
    upload(client, admin, fixture_csv("abc_chain"), name="retire")
    run_worker(app)
    with rt.session_factory() as db:
        snap = db.execute(select(GraphSnapshot).where(GraphSnapshot.purpose == "OPERATIONAL")).scalar_one()
    GraphService(rt).retire(snap.graph_snapshot_id)
    left = rt.graph.run("MATCH (n {snapshot_id:$s}) RETURN count(n) AS n", {"s": str(snap.graph_snapshot_id)})
    assert left[0]["n"] == 0
    with rt.session_factory() as db:
        assert db.get(GraphSnapshot, snap.graph_snapshot_id).status == "RETIRED"
