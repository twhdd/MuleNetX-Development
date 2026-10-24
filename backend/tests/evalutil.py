"""Evaluation setup: the synthetic dataset plus a dense fraud cluster in the test window (six accounts R0..R5
transferring to each other in the last four steps), which the pipeline flags as a potential fraud ring."""

from __future__ import annotations

from typing import Any

from mulenetx.api.deps import get_services
from tests.apiutil import _Req
from tests.ingestutil import run_worker
from tests.seed import seed_dataset
from tests.synth import generate


def seed_with_ring(app: Any, client: Any, admin: Any, key: str) -> Any:
    edges, fraud, types = generate(customers=300, mules=30, steps=60, seed=11)
    ring = [f"R{i}" for i in range(6)]
    for step in (56, 57, 58, 59):
        for i in range(6):
            for offset, amount in ((1, 9000.0), (2, 7000.0)):
                fraud.add(len(edges))
                edges.append((ring[i], ring[(i + offset) % 6], amount + i, step))
                types.append("TRANSFER")
    ds = seed_dataset(get_services(_Req(app)).runtime, edges, key=key, fraud=fraud, types=types)
    resp = client.post("/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers)
    assert resp.status_code == 202, resp.text
    run_worker(app, timeout=600)
    return ds


def evaluate(app: Any, client: Any, admin: Any) -> dict[str, Any]:
    resp = client.post("/api/v1/evaluation/runs", json={}, headers=admin.headers)
    assert resp.status_code == 202, resp.text
    run_worker(app, timeout=600)
    summary: dict[str, Any] = client.get(
        f"/api/v1/evaluation/runs/{resp.json()['evaluation_run_id']}", headers=admin.headers
    ).json()
    assert summary["status"] == "COMPLETED", summary
    return summary


def metric(summary: dict[str, Any], level: str, name: str) -> dict[str, Any]:
    found: dict[str, Any] = next(m for m in summary["levels"][level] if m["metric"] == name)
    return found
