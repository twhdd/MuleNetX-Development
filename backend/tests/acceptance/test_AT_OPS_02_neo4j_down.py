"""AT-OPS-02: with Neo4j down, relational features keep working and `/ready` stays 200 with neo4j DOWN
(SRS §26.3); graph endpoints answer 503 GRAPH_UNAVAILABLE instead of fabricating data (§25.4).

The in-process test points a second app at a closed Bolt port. The docker test stops the Compose stack's
Neo4j container and checks the real backend."""

from __future__ import annotations

import time

import httpx
import pytest
from fastapi.testclient import TestClient

from mulenetx.main import create_app
from tests.apiutil import UserFactory
from tests.caseutil import new_case
from tests.conftest import FAST_ARGON, make_settings
from tests.ingestutil import seed_synth_and_activate


@pytest.mark.integration
def test_AT_OPS_02_neo4j_down_in_process(app, client, users, clean_db) -> None:
    admin = users("ADMIN")
    seed_synth_and_activate(app, client, admin, key="o2")
    down = create_app(make_settings(postgres_dsn=clean_db, neo4j_uri="bolt://127.0.0.1:1", **FAST_ARGON))
    with TestClient(down) as c:
        ready = c.get("/ready")
        assert ready.status_code == 200
        body = ready.json()
        assert body["status"] == "READY" and body["components"]["neo4j"] == "DOWN"
        assert body["components"]["postgres"] == "UP"
        assert c.get("/health").json() == {"status": "UP"}
        inv = UserFactory(down)("INVESTIGATOR")
        h = inv.headers
        acc = "o2:C90000"
        for url in (
            f"/api/v1/accounts/{acc}",
            f"/api/v1/accounts/{acc}/risk",
            f"/api/v1/accounts/{acc}/transactions",
            f"/api/v1/accounts/{acc}/features",
            f"/api/v1/accounts/{acc}/shap",
            "/api/v1/accounts",
            "/api/v1/context",
            "/api/v1/communities",
            "/api/v1/graph/metrics?account_id=o2:C90000",
        ):
            assert c.get(url, headers=h).status_code == 200, url
        case = new_case(c, inv)
        assert (
            c.post(
                f"/api/v1/cases/{case['case_id']}/subjects",
                json={"subject_type": "ACCOUNT", "subject_id": acc},
                headers=h,
            ).status_code
            == 201
        )
        for url, params in (
            ("/api/v1/graph/neighborhood", {"account_id": acc}),
            ("/api/v1/graph/path", {"source_account_id": acc, "destination_account_id": "o2:C00001"}),
        ):
            resp = c.get(url, params=params, headers=h)
            assert resp.status_code == 503 and resp.json()["error"]["code"] == "GRAPH_UNAVAILABLE", url


@pytest.mark.docker
def test_AT_OPS_02_neo4j_down_compose() -> None:
    from tests.acceptance.test_AT_OPS_01_clean_startup import _compose, _wait_ready

    assert _compose("up", "-d").returncode == 0
    _wait_ready("http://127.0.0.1:8000/ready")
    try:
        assert _compose("stop", "neo4j").returncode == 0
        deadline = time.monotonic() + 60
        body: dict[str, object] = {}
        while time.monotonic() < deadline:
            resp = httpx.get("http://127.0.0.1:8000/ready", timeout=10)
            body = resp.json()
            if resp.status_code == 200 and body["components"]["neo4j"] == "DOWN":  # type: ignore[index]
                break
            time.sleep(2)
        assert body["components"]["neo4j"] == "DOWN", body  # type: ignore[index]
        assert httpx.get("http://127.0.0.1:8000/ready", timeout=10).status_code == 200
        assert httpx.get("http://127.0.0.1:8000/health", timeout=10).status_code == 200
        # the dashboard keeps proxying the API while the graph store is down
        assert httpx.get("http://127.0.0.1:8080/ready", timeout=10).status_code == 200
    finally:
        _compose("start", "neo4j")
