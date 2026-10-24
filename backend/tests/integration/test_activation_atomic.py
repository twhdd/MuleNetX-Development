"""Activation is one transaction (SRS §6.9): a failure in step 2 leaves the previous context active."""

import pytest
from sqlalchemy import select, text

from mulenetx.activation import service as activation
from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import ActiveContext
from tests.apiutil import _Req
from tests.ingestutil import run_worker, seed_and_activate

pytestmark = pytest.mark.integration


def test_activation_failure_keeps_previous_context(app, client, users, monkeypatch: pytest.MonkeyPatch) -> None:
    admin = users("ADMIN")
    ds = seed_and_activate(app, client, admin, [("CA", "CB", 1.0, 1)], key="act")
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        before = db.execute(select(ActiveContext)).scalar_one()
        before_values = (before.graph_snapshot_id, before.updated_by_pipeline_run_id, before.updated_at)

    def broken(session, run):  # type: ignore[no-untyped-def]
        raise RuntimeError("injected failure in projection update (step 2)")

    monkeypatch.setattr(activation, "update_projections", broken)
    run_id = client.post(
        "/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers
    ).json()["pipeline_run_id"]
    run_worker(app)
    run = client.get(f"/api/v1/pipeline-runs/{run_id}", headers=admin.headers).json()
    assert run["current_state"] == "FAILED" and run["resumable_from"] == "RING_ANALYSIS"
    with rt.session_factory() as db:
        after = db.execute(select(ActiveContext)).scalar_one()
        assert (after.graph_snapshot_id, after.updated_by_pipeline_run_id, after.updated_at) == before_values
    with rt.engine.connect() as conn:
        activated = [
            r[0] for r in conn.execute(text("SELECT resource_id FROM audit_events WHERE action='pipeline.activate'"))
        ]
    assert activated and run_id not in activated
