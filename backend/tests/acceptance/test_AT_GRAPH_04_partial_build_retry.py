"""AT-GRAPH-04: a build that fails midway leaves the previous snapshot active; the retry succeeds and the
new snapshot has no orphan or duplicate nodes."""

import pytest
from sqlalchemy import select, text

from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import ActiveContext, GraphSnapshot
from mulenetx.graph.build import GraphBuilder
from mulenetx.main import create_app
from tests.apiutil import UserFactory, _Req
from tests.conftest import FAST_ARGON, make_settings
from tests.ingestutil import run_worker, seed_and_activate
from tests.seed import seed_dataset

pytestmark = pytest.mark.integration


def test_AT_GRAPH_04_partial_build_retry(clean_db, clean_graph, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    app = create_app(make_settings(postgres_dsn=clean_db, graph_build_batch_size=1, **FAST_ARGON))
    rt = get_services(_Req(app)).runtime
    with TestClient(app) as client:
        admin = UserFactory(app)("ADMIN")
        seed_and_activate(app, client, admin, [("CA", "CB", 1.0, 1), ("CB", "CC", 2.0, 2)], key="g4a")
        with rt.session_factory() as db:
            first = db.execute(select(ActiveContext)).scalar_one().graph_snapshot_id
        assert first is not None

        # a new dataset version whose build fails after the first transaction batch
        original = GraphBuilder.write_transaction_batch
        calls = {"n": 0}

        def flaky(self, sid, rows):  # type: ignore[no-untyped-def]
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("injected neo4j failure after the first batch")
            return original(self, sid, rows)

        monkeypatch.setattr(GraphBuilder, "write_transaction_batch", flaky)
        ds_b = seed_dataset(rt, [("CA", "CB", 3.0, 1), ("CB", "CC", 4.0, 2)], key="g4b")
        run2 = client.post(
            "/api/v1/pipeline-runs", json={"dataset_id": str(ds_b.dataset_id)}, headers=admin.headers
        ).json()["pipeline_run_id"]
        run_worker(app)
        failed = client.get(f"/api/v1/pipeline-runs/{run2}", headers=admin.headers).json()
        assert failed["current_state"] == "FAILED" and failed["resumable_from"] == "GRAPH_BUILDING"
        second = failed["graph_snapshot_id"]
        with rt.session_factory() as db:
            assert db.execute(select(ActiveContext)).scalar_one().graph_snapshot_id == first
            assert db.get(GraphSnapshot, second).status == "FAILED"
        partial = rt.graph.run("MATCH (t:Transaction {snapshot_id:$s}) RETURN count(t) AS n", {"s": second})[0]["n"]
        assert partial == 1  # the first batch landed, then the build failed
        # the active snapshot is untouched
        active_nodes = rt.graph.run("MATCH (n {snapshot_id:$s}) RETURN count(n) AS n", {"s": str(first)})[0]["n"]
        assert active_nodes == 5

        monkeypatch.setattr(GraphBuilder, "write_transaction_batch", original)
        assert client.post(f"/api/v1/pipeline-runs/{run2}/retry", headers=admin.headers).status_code == 202
        run_worker(app)
        done = client.get(f"/api/v1/pipeline-runs/{run2}", headers=admin.headers).json()
        assert done["current_state"] == "READY"
        assert done["graph_snapshot_id"] == second  # the same snapshot ID was rebuilt
        counts = rt.graph.run(
            "MATCH (n {snapshot_id:$s}) RETURN labels(n)[0] AS l, count(n) AS n ORDER BY l", {"s": second}
        )
        assert {c["l"]: c["n"] for c in counts} == {"Account": 3, "Transaction": 2}
        with rt.engine.connect() as conn:
            snap = conn.execute(
                text("SELECT status, node_count FROM graph_snapshots WHERE graph_snapshot_id=:s"), {"s": second}
            ).one()
        assert (snap.status, snap.node_count) == ("READY", 5)
