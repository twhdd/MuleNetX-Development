"""A context whose model was trained on another dataset's test window cannot be evaluated: the run fails with
a clear message, and reading the failed run works (regression: the failure lookup used a missing column)."""

import pytest

from mulenetx.api.deps import get_services
from tests.apiutil import _Req
from tests.ingestutil import run_worker, seed_synth_and_activate
from tests.seed import seed_dataset
from tests.synth import generate

pytestmark = pytest.mark.integration


def test_failed_evaluation_is_readable(app, client, users) -> None:
    admin = users("ADMIN")
    seed_synth_and_activate(app, client, admin, key="fa")  # trains the model (T_test = end of this dataset)
    edges, fraud, types = generate(customers=300, mules=30, steps=80, seed=5)  # a longer dataset reuses it
    ds = seed_dataset(get_services(_Req(app)).runtime, edges, key="fb", fraud=fraud, types=types)
    client.post("/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers)
    run_worker(app, timeout=600)
    ctx = client.get("/api/v1/context", headers=admin.headers).json()
    assert ctx["dataset_id"] == str(ds.dataset_id)
    run_id = client.post("/api/v1/evaluation/runs", json={}, headers=admin.headers).json()["evaluation_run_id"]
    run_worker(app, timeout=600)
    s = client.get(f"/api/v1/evaluation/runs/{run_id}", headers=admin.headers)
    assert s.status_code == 200, s.text
    body = s.json()
    assert body["status"] == "FAILED", body  # the reused model's test window ends before this snapshot's cutoff
    assert "test cutoff" in body["failure"]
    assert client.get("/api/v1/evaluation/runs", headers=admin.headers).status_code == 200
    assert client.get(f"/api/v1/evaluation/runs/{run_id}/RING", headers=admin.headers).status_code == 409
