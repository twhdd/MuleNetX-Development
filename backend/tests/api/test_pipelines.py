"""Pipeline runs, retry, models and context APIs (SRS §7.6–§7.7, §19.2)."""

import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from mulenetx.jobs.handlers import build_handlers
from mulenetx.jobs.runner import Runner
from tests.apiutil import _Req, audit_events
from tests.seed import seed_dataset

pytestmark = pytest.mark.integration

ABC = [("A", "B", 10.0, 1), ("B", "C", 5.0, 2)]


def _runner(app) -> Runner:
    return Runner(get_services(_Req(app)).runtime, build_handlers(), worker="test-worker")


def test_pipeline_walks_every_state_to_ready(app, client, users) -> None:
    rt = get_services(_Req(app)).runtime
    ds = seed_dataset(rt, ABC)
    admin = users("ADMIN")
    resp = client.post("/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers)
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["pipeline_run_id"]
    assert resp.json()["status"] == "CREATED"

    second = client.post("/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers)
    assert second.status_code == 409 and second.json()["error"]["code"] == "PIPELINE_ALREADY_RUNNING"

    runner = _runner(app)
    runner.drain(timeout=60)
    runner.shutdown()

    body = client.get(f"/api/v1/pipeline-runs/{run_id}", headers=admin.headers).json()
    assert body["current_state"] == "READY", body
    assert body["graph_snapshot_id"] and body["analytics_run_id"] and body["completed_at"]
    with rt.engine.connect() as conn:
        stages = [
            r[0]
            for r in conn.execute(
                text("SELECT payload->>'stage' FROM jobs WHERE payload->>'pipeline_run_id'=:r ORDER BY created_at"),
                {"r": run_id},
            )
        ]
    assert stages == [
        "INGESTING",
        "PROFILING",
        "GRAPH_BUILDING",
        "ANALYTICS_RUNNING",
        "FEATURES_RUNNING",
        "TRAINING",
        "SCORING",
        "RING_ANALYSIS",
    ]
    metrics = body["metrics"]
    assert metrics["records_accepted"] == 2 and metrics["job_attempts"] == 8
    assert "graph_build_duration" in metrics

    ctx = client.get("/api/v1/context", headers=admin.headers).json()
    assert ctx["dataset_id"] == str(ds.dataset_id) and ctx["updated_by_pipeline_run_id"] == run_id
    assert ctx["is_synthetic_injection"] is False  # §7.10: injection is disabled by default
    assert any(e.action == "pipeline.activate" for e in audit_events(app))
    assert any(e.action == "pipeline.start" for e in audit_events(app))

    listed = client.get("/api/v1/pipeline-runs", params={"dataset_id": str(ds.dataset_id)}, headers=admin.headers)
    assert listed.json()["total"] == 1


def test_failure_and_retry_resumes_stage(app, client, users) -> None:
    rt = get_services(_Req(app)).runtime
    ds = seed_dataset(rt, ABC, key="rt")
    admin = users("ADMIN")
    run_id = client.post(
        "/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers
    ).json()["pipeline_run_id"]
    # make GRAPH_BUILDING fail: the ingestion run is temporarily not SUCCEEDED (prerequisite missing)
    runner = _runner(app)
    for _ in range(40):
        runner.tick()
        # let the claimed jobs finish before reading the state, so no later stage is claimed past PROFILED
        for running in list(runner.running.values()):
            running.future.result(timeout=30)
        state = client.get(f"/api/v1/pipeline-runs/{run_id}", headers=admin.headers).json()["current_state"]
        if state == "PROFILED":
            break
    assert state == "PROFILED"
    with rt.engine.begin() as conn:
        conn.execute(
            text("UPDATE ingestion_runs SET status='FAILED' WHERE ingestion_run_id=:i"), {"i": ds.ingestion_run_id}
        )
    runner.drain(timeout=30)
    failed = client.get(f"/api/v1/pipeline-runs/{run_id}", headers=admin.headers).json()
    assert failed["current_state"] == "FAILED"
    assert failed["resumable_from"] == "GRAPH_BUILDING"
    assert failed["failure_category"] == "PIPELINE_PREREQUISITE_MISSING"

    blocked = client.post(f"/api/v1/pipeline-runs/{run_id}/retry", headers=admin.headers)
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "PIPELINE_PREREQUISITE_MISSING"

    with rt.engine.begin() as conn:
        conn.execute(
            text("UPDATE ingestion_runs SET status='SUCCEEDED' WHERE ingestion_run_id=:i"), {"i": ds.ingestion_run_id}
        )
    alias = client.post(f"/api/v1/ingestion/{ds.ingestion_run_id}/retry", headers=admin.headers)
    assert alias.status_code == 202, alias.text
    assert alias.headers["deprecation"] == "true" and f"/pipeline-runs/{run_id}/retry" in alias.headers["link"]
    runner.drain(timeout=60)
    runner.shutdown()
    done = client.get(f"/api/v1/pipeline-runs/{run_id}", headers=admin.headers).json()
    assert done["current_state"] == "READY"
    again = client.post(f"/api/v1/pipeline-runs/{run_id}/retry", headers=admin.headers)
    assert again.status_code == 409


def test_start_requires_ingested_dataset(client, users) -> None:
    admin = users("ADMIN")
    missing = client.post(
        "/api/v1/pipeline-runs", json={"dataset_id": "00000000-0000-4000-8000-000000000009"}, headers=admin.headers
    )
    assert missing.status_code == 404


def test_models_and_context_empty(client, users) -> None:
    analyst = users("ANALYST")
    models = client.get("/api/v1/models", headers=analyst.headers)
    assert models.status_code == 200 and models.json()["items"] == []
    assert client.get("/api/v1/models/none", headers=analyst.headers).status_code == 404
    ctx = client.get("/api/v1/context", headers=analyst.headers).json()
    assert ctx["is_active"] is False and ctx["dataset_id"] is None


def test_page_and_filter_validation(client, users) -> None:
    analyst = users("ANALYST")
    assert client.get("/api/v1/pipeline-runs", params={"page_size": 101}, headers=analyst.headers).status_code == 400
    assert client.get("/api/v1/pipeline-runs", params={"state": "BOGUS"}, headers=analyst.headers).status_code == 400
