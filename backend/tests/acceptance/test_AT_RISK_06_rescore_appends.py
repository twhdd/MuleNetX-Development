"""AT-RISK-06: rescoring creates a new assessment row; the prior row is unchanged."""

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.account_analytics import RiskAssessment
from tests.apiutil import _Req
from tests.ingestutil import run_worker, seed_synth_and_activate

pytestmark = pytest.mark.integration


def test_AT_RISK_06_rescore_appends(app, client, users) -> None:
    admin = users("ADMIN")
    ds, first_run = seed_synth_and_activate(app, client, admin, key="r6")
    rt = get_services(_Req(app)).runtime
    account = "r6:C90000"
    with rt.session_factory() as db:
        before = db.execute(select(RiskAssessment).where(RiskAssessment.account_id == account)).scalar_one()
        snapshot_before = {c: getattr(before, c) for c in RiskAssessment.__table__.columns.keys()}
    resp = client.post("/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers)
    assert resp.status_code == 202
    run_worker(app, timeout=600)
    second = client.get(f"/api/v1/pipeline-runs/{resp.json()['pipeline_run_id']}", headers=admin.headers).json()
    assert second["current_state"] == "READY" and second["scoring_run_id"] != first_run["scoring_run_id"]
    assert second["model_version"] == first_run["model_version"]  # compatible model reused, no retraining
    with rt.session_factory() as db:
        rows = (
            db.execute(
                select(RiskAssessment).where(RiskAssessment.account_id == account).order_by(RiskAssessment.generated_at)
            )
            .scalars()
            .all()
        )
        assert len(rows) == 2
        old = db.get(RiskAssessment, before.assessment_id)
        assert {c: getattr(old, c) for c in RiskAssessment.__table__.columns.keys()} == snapshot_before
    history = client.get(f"/api/v1/accounts/{account}/risk/history", headers=admin.headers).json()
    assert history["total"] == 2
    stale = [h["is_stale"] for h in history["items"]]
    assert sorted(stale) == [False, True]
