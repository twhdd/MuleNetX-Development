"""AT-ML-04: when no model can be trained, the pipeline still reaches READY with the ML component unavailable
and no historical score is substituted (§7.6 rule 4, §11.12). The risk-API half is asserted in T19."""

import pytest
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.db.models.lineage import ModelVersion, RiskLogicVersion
from tests.apiutil import _Req
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def test_AT_ML_04_no_model_pipeline_still_ready(app, client, users) -> None:
    admin = users("ADMIN")
    edges = [(f"C{i}", f"C{i + 1}", 10.0 + i, i) for i in range(30)]  # no fraud labels → no positives
    seed_and_activate(app, client, admin, edges, key="noml")
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        assert db.execute(select(ModelVersion)).first() is None
        rl = db.execute(select(RiskLogicVersion)).scalars().all()
    assert len(rl) == 1  # the risk logic version is still created (§11 / PLAN T17)
    assert rl[0].normalization_reference["model_version"] is None
    assert "positive and negative" in rl[0].normalization_reference["training_failure"]
    ctx = client.get("/api/v1/context", headers=admin.headers).json()
    assert ctx["model_version"] is None and ctx["is_active"] is True


def test_AT_ML_04_historical_score_not_substituted(app, client, users) -> None:
    """A later scoring run whose model artifact is unavailable reports ML UNAVAILABLE; the previous run's ML
    score is not shown as current."""
    from pathlib import Path

    from tests.ingestutil import run_worker, seed_synth_and_activate

    admin = users("ADMIN")
    ds, first = seed_synth_and_activate(app, client, admin, key="ml4")
    account = "ml4:C90000"
    before = client.get(f"/api/v1/accounts/{account}/risk", headers=admin.headers).json()
    assert before["ml_score"] is not None
    rt = get_services(_Req(app)).runtime
    with rt.session_factory() as db:
        artifact = Path(db.get(ModelVersion, first["model_version"]).artifact_reference)
    hidden = artifact.with_suffix(".hidden")
    artifact.rename(hidden)
    try:
        run_id = client.post(
            "/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers
        ).json()["pipeline_run_id"]
        run_worker(app, timeout=600)
    finally:
        hidden.rename(artifact)
    run = client.get(f"/api/v1/pipeline-runs/{run_id}", headers=admin.headers).json()
    assert run["current_state"] == "READY"
    now = client.get(f"/api/v1/accounts/{account}/risk", headers=admin.headers).json()
    assert now["ml_score"] is None
    assert now["signal_availability"]["ml"] == {"state": "UNAVAILABLE", "reason": "MODEL_UNAVAILABLE"}
    assert now["model_version"] is None and now["lineage"]["scoring_run_id"] == run["scoring_run_id"]
    assert now["signal_coverage"] == 0.5
    old = client.get(
        f"/api/v1/accounts/{account}/risk", params={"scoring_run_id": first["scoring_run_id"]}, headers=admin.headers
    ).json()
    assert old["ml_score"] == before["ml_score"] and old["is_stale"] is True
