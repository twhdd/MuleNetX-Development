"""Ingestion test helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mulenetx.api.deps import get_services
from mulenetx.jobs.handlers import build_handlers
from mulenetx.jobs.runner import Runner
from tests.apiutil import Actor, _Req

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture_csv(name: str) -> Path:
    return FIXTURES / name / "transactions.csv"


def expected(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name / "expected.json").read_text())


def upload(
    client: TestClient,
    actor: Actor,
    path: Path,
    name: str = "fixture",
    version: str = "v1",
    content_type: str = "text/csv",
    adapter_config: dict[str, Any] | None = None,
) -> Any:
    with path.open("rb") as f:
        return client.post(
            "/api/v1/ingestion",
            headers=actor.headers,
            files={"file": (path.name, f, content_type)},
            data={
                "name": name,
                "source": "paysim-fixture",
                "dataset_version": version,
                "schema_version": "paysim-1",
                "adapter": "paysim-v1",
                "adapter_config": json.dumps(adapter_config or {}),
            },
        )


def run_worker(app: FastAPI, timeout: float = 120) -> None:
    runner = Runner(get_services(_Req(app)).runtime, build_handlers(), worker="test-worker")
    try:
        runner.drain(timeout=timeout)
    finally:
        runner.shutdown()


def seed_and_activate(
    app: FastAPI, client: TestClient, admin: Actor, edges: list[tuple[str, str, float, int]], key: str = "fx"
) -> Any:
    """Seed canonical rows directly, run the pipeline to READY, return the SeededDataset."""
    from tests.seed import seed_dataset

    ds = seed_dataset(get_services(_Req(app)).runtime, edges, key=key)
    resp = client.post("/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers)
    assert resp.status_code == 202, resp.text
    run_worker(app)
    run = client.get(f"/api/v1/pipeline-runs/{resp.json()['pipeline_run_id']}", headers=admin.headers).json()
    assert run["current_state"] == "READY", run
    return ds


def seed_synth_and_activate(app: FastAPI, client: TestClient, admin: Actor, key: str = "syn", **kwargs: Any) -> Any:
    """Seed the synthetic labelled dataset (tests/synth.py) and run the full pipeline to READY."""
    from tests.seed import seed_dataset
    from tests.synth import generate

    edges, fraud, types = generate(**kwargs)
    ds = seed_dataset(get_services(_Req(app)).runtime, edges, key=key, fraud=fraud, types=types)
    resp = client.post("/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers)
    assert resp.status_code == 202, resp.text
    run_worker(app, timeout=600)
    run = client.get(f"/api/v1/pipeline-runs/{resp.json()['pipeline_run_id']}", headers=admin.headers).json()
    assert run["current_state"] == "READY", run
    return ds, run
