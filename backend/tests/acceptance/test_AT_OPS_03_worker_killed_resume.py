"""AT-OPS-03: a worker killed mid-stage loses its lease; after expiry the stage resumes on another worker and
the pipeline reaches READY.

`test_AT_OPS_03_in_process` simulates the crash deterministically (heartbeat stops and the dead worker's
database connections are terminated, releasing its advisory lock). `test_AT_OPS_03_docker` kills the real
worker container of the Compose stack.
"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from mulenetx.graph.build import GraphBuilder
from mulenetx.jobs.handlers import build_handlers
from mulenetx.jobs.runner import Runner
from mulenetx.main import create_app
from tests.apiutil import UserFactory, _Req
from tests.conftest import FAST_ARGON, make_settings
from tests.seed import seed_dataset


@pytest.mark.integration
def test_AT_OPS_03_in_process(clean_db, clean_graph, monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    app = create_app(
        make_settings(
            postgres_dsn=clean_db,
            graph_build_batch_size=1,
            job_lease_seconds=2,
            job_heartbeat_seconds=0.5,
            **FAST_ARGON,
        )
    )
    rt = get_services(_Req(app)).runtime
    edges = [(f"C{i}", f"C{i + 1}", 10.0 + i, i) for i in range(6)]
    ds = seed_dataset(rt, edges, key="ops3")
    entered, release = threading.Event(), threading.Event()
    original = GraphBuilder.write_transaction_batch
    state = {"dead": False}

    def crashing(self, sid, rows):  # type: ignore[no-untyped-def]
        if not state["dead"]:
            state["dead"] = True
            entered.set()
            release.wait(30)
            raise RuntimeError("this worker is dead")
        return original(self, sid, rows)

    monkeypatch.setattr(GraphBuilder, "write_transaction_batch", crashing)
    with TestClient(app) as client:
        admin = UserFactory(app)("ADMIN")
        run_id = client.post(
            "/api/v1/pipeline-runs", json={"dataset_id": str(ds.dataset_id)}, headers=admin.headers
        ).json()["pipeline_run_id"]
        doomed = Runner(rt, build_handlers(), worker="doomed")
        while not entered.is_set():
            doomed.tick()
            time.sleep(0.05)
        assert (
            client.get(f"/api/v1/pipeline-runs/{run_id}", headers=admin.headers).json()["current_state"]
            == "GRAPH_BUILDING"
        )
        # the process dies: no more heartbeats, and its connections (with the advisory lock) are gone
        for r in doomed.running.values():
            r.heartbeat.stop()
        with rt.engine.begin() as conn:
            conn.execute(
                text("SELECT pg_terminate_backend(l.pid) FROM pg_locks l WHERE l.locktype = 'advisory' AND l.granted")
            )
        time.sleep(2.5)  # lease expiry

        survivor = Runner(rt, build_handlers(), worker="survivor")
        survivor.drain(timeout=60)
        release.set()
        survivor.shutdown()
        doomed.shutdown()
        run = client.get(f"/api/v1/pipeline-runs/{run_id}", headers=admin.headers).json()
        assert run["current_state"] == "READY", run
        assert run["metrics"]["lease_expirations"] >= 1
        sid = run["graph_snapshot_id"]
        counts = rt.graph.run(
            "MATCH (n {snapshot_id:$s}) RETURN labels(n)[0] AS l, count(n) AS n ORDER BY l", {"s": sid}
        )
        assert {c["l"]: c["n"] for c in counts} == {"Account": 7, "Transaction": 6}


ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ["docker", "compose", "-f", str(ROOT / "docker-compose.yml"), "--project-directory", str(ROOT)]
HEADER = (
    "step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,"
    "isFraud,isFlaggedFraud\n"
)


def _env() -> dict[str, str]:
    values = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    return values


@pytest.mark.docker
def test_AT_OPS_03_docker(tmp_path: Path) -> None:
    env = _env()
    base = "http://127.0.0.1:8000"
    subprocess.run(
        [*COMPOSE, "exec", "-T", "backend", "python", "-m", "mulenetx.cli", "bootstrap-admin"],
        capture_output=True,
        text=True,
        check=False,
    )
    token = httpx.post(
        f"{base}/api/v1/auth/login",
        json={
            "username": env["MULENETX_BOOTSTRAP_ADMIN_USERNAME"],
            "password": env["MULENETX_BOOTSTRAP_ADMIN_PASSWORD"],
        },
        timeout=10,
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    csv = tmp_path / "ops3.csv"
    with csv.open("w") as f:
        f.write(HEADER)
        for i in range(60_000):
            f.write(f"{i // 1000},TRANSFER,{10 + i % 97}.25,C{i % 7919},0,0,C{(i * 31) % 7919 + 1},0,0,0,0\n")
    with csv.open("rb") as f:
        resp = httpx.post(
            f"{base}/api/v1/ingestion",
            headers=headers,
            timeout=60,
            files={"file": ("ops3.csv", f, "text/csv")},
            data={
                "name": f"ops3 {time.time_ns()}",
                "source": "test",
                # the file is identical on every run; a new version keeps a rerun on the same stack from
                # being (correctly) refused as DATASET_ALREADY_REGISTERED
                "dataset_version": f"v{time.time_ns()}",
                "schema_version": "paysim-1",
                "adapter": "paysim-v1",
            },
        )
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["pipeline_run_id"]

    def state() -> str:
        return str(
            httpx.get(f"{base}/api/v1/pipeline-runs/{run_id}", headers=headers, timeout=10).json()["current_state"]
        )

    deadline = time.monotonic() + 300
    while state() != "GRAPH_BUILDING":
        assert time.monotonic() < deadline and state() not in ("FAILED", "READY")
        time.sleep(0.5)
    killed = subprocess.run(["docker", "kill", "mulenetx-worker-1"], capture_output=True, text=True, check=False)
    assert killed.returncode == 0, killed.stderr
    subprocess.run([*COMPOSE, "up", "-d", "worker"], capture_output=True, text=True, check=False)
    deadline = time.monotonic() + 600
    while (current := state()) != "READY":
        assert current != "FAILED", httpx.get(f"{base}/api/v1/pipeline-runs/{run_id}", headers=headers).text
        assert time.monotonic() < deadline, "pipeline did not reach READY after the worker restart"
        time.sleep(3)
    metrics = httpx.get(f"{base}/api/v1/pipeline-runs/{run_id}", headers=headers, timeout=10).json()["metrics"]
    assert metrics["lease_expirations"] >= 1
