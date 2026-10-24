"""AT-API-01: every implemented endpoint and alias, called with a valid request, returns its documented SRS
§19.2 success status and a body that validates against its OpenAPI schema. Aliases carry `Deprecation` and
`Link` headers and return their target's body (§19.2.1)."""

from typing import Any

import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from mulenetx.jobs.handlers import build_handlers
from mulenetx.jobs.runner import Runner
from tests.apiutil import PASSWORD, _Req
from tests.caseutil import new_case
from tests.ingestutil import fixture_csv, seed_synth_and_activate, upload
from tests.openapiutil import norm, operations, srs_aliases, srs_rows, validate
from tests.seed import seed_dataset

pytestmark = pytest.mark.integration

ABC = [("A", "B", 100.0, 1), ("B", "C", 90.0, 2)]


class Caller:
    def __init__(self, client, headers) -> None:
        self.client = client
        self.headers = headers
        self.called: set[tuple[str, str]] = set()
        self.bodies: dict[tuple[str, str], Any] = {}

    def __call__(self, method: str, template: str, url: str, status: int, headers=None, **kw: Any) -> Any:
        resp = self.client.request(method, url, headers=headers or self.headers, **kw)
        assert resp.status_code == status, f"{method} {url}: {resp.status_code} {resp.text[:300]}"
        key = (method, norm(template))
        self.called.add(key)
        if status == 204:
            assert resp.content == b""
            return resp
        assert resp.headers["content-type"].startswith("application/json")
        validate(method, template, status, resp.json())
        self.bodies[key] = resp.json()
        return resp


def _fail_at_graph_building(call: Caller, app, client, admin, key: str) -> tuple[str, Any]:
    """Run a fresh dataset's pipeline until GRAPH_BUILDING fails on a missing prerequisite (as test_pipelines)."""
    rt = get_services(_Req(app)).runtime
    ds = seed_dataset(rt, ABC, key=key)
    started = call(
        "POST", "/api/v1/pipeline-runs", "/api/v1/pipeline-runs", 202, json={"dataset_id": str(ds.dataset_id)}
    )
    run_id = started.json()["pipeline_run_id"]
    runner = Runner(rt, build_handlers(), worker="test-worker")
    try:
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
        with rt.engine.begin() as conn:
            conn.execute(
                text("UPDATE ingestion_runs SET status='SUCCEEDED' WHERE ingestion_run_id=:i"),
                {"i": ds.ingestion_run_id},
            )
    finally:
        runner.shutdown()
    assert client.get(f"/api/v1/pipeline-runs/{run_id}", headers=admin.headers).json()["current_state"] == "FAILED"
    return run_id, ds


def test_AT_API_01_every_endpoint(app, client, users) -> None:
    admin = users("ADMIN")
    ds, run = seed_synth_and_activate(app, client, admin, key="api")
    call = Caller(client, admin.headers)
    acc = "api:C90000"
    a = f"/api/v1/accounts/{acc}"

    call("GET", "/health", "/health", 200)
    call("GET", "/ready", "/ready", 200)
    call("GET", "/api/v1/auth/me", "/api/v1/auth/me", 200)
    call("GET", "/api/v1/users", "/api/v1/users", 200)
    new_user = call(
        "POST",
        "/api/v1/users",
        "/api/v1/users",
        201,
        json={"username": "api-user", "role": "ANALYST", "password": PASSWORD},
    ).json()
    call("PATCH", "/api/v1/users/{id}", f"/api/v1/users/{new_user['user_id']}", 200, json={"role": "INVESTIGATOR"})
    login = call(
        "POST",
        "/api/v1/auth/login",
        "/api/v1/auth/login",
        200,
        headers={},
        json={"username": "api-user", "password": PASSWORD},
    ).json()
    call(
        "POST",
        "/api/v1/auth/logout",
        "/api/v1/auth/logout",
        204,
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )

    ctx = call("GET", "/api/v1/context", "/api/v1/context", 200).json()
    call("GET", "/api/v1/ingestion", "/api/v1/ingestion", 200)
    call("GET", "/api/v1/ingestion/{id}", f"/api/v1/ingestion/{ds.ingestion_run_id}", 200)
    call("GET", "/api/v1/datasets/{id}/profile", f"/api/v1/datasets/{ds.dataset_id}/profile", 200)
    call("GET", "/api/v1/pipeline-runs", "/api/v1/pipeline-runs", 200)
    call("GET", "/api/v1/pipeline-runs/{id}", f"/api/v1/pipeline-runs/{run['pipeline_run_id']}", 200)
    call("GET", "/api/v1/models", "/api/v1/models", 200)
    call("GET", "/api/v1/models/{version}", f"/api/v1/models/{ctx['model_version']}", 200)

    call("GET", "/api/v1/accounts", "/api/v1/accounts", 200, params={"q": "C9", "page_size": 5})
    call("GET", "/api/v1/accounts/{id}", a, 200)
    call("GET", "/api/v1/accounts/{id}/transactions", f"{a}/transactions", 200, params={"page_size": 5})
    risk = call("GET", "/api/v1/accounts/{id}/risk", f"{a}/risk", 200).json()
    call("GET", "/api/v1/accounts/{id}/risk/history", f"{a}/risk/history", 200)
    call("GET", "/api/v1/accounts/{id}/risk/propagation", f"{a}/risk/propagation", 200)
    call("GET", "/api/v1/accounts/{id}/features", f"{a}/features", 200)
    call("GET", "/api/v1/accounts/{id}/temporal", f"{a}/temporal", 200)
    call("GET", "/api/v1/accounts/{id}/shap", f"{a}/shap", 200, params={"assessment_id": risk["assessment_id"]})
    call("GET", "/api/v1/accounts/{id}/community", f"{a}/community", 200)
    call("GET", "/api/v1/accounts/{id}/motifs", f"{a}/motifs", 200)

    rings = call("GET", "/api/v1/rings", "/api/v1/rings", 200, params={"page_size": 100}).json()["items"]
    pot = next(r for r in rings if r["candidate_class"] == "POTENTIAL_FRAUD_RING_CANDIDATE")["ring_id"]
    r = f"/api/v1/rings/{pot}"
    call("GET", "/api/v1/rings/{id}", r, 200)
    call("GET", "/api/v1/rings/{id}/accounts", f"{r}/accounts", 200)
    call("GET", "/api/v1/rings/{id}/transactions", f"{r}/transactions", 200)
    call("GET", "/api/v1/rings/{id}/features", f"{r}/features", 200)
    call("GET", "/api/v1/rings/{id}/risk", f"{r}/risk", 200)
    call("GET", "/api/v1/rings/{id}/evidence", f"{r}/evidence", 200, params={"page_size": 5})
    call("GET", "/api/v1/rings/{id}/motifs", f"{r}/motifs", 200)
    ring_alias = call("GET", "/api/v1/fraud-ring-candidates", "/api/v1/fraud-ring-candidates", 200)
    assert ring_alias.headers["deprecation"] == "true"
    call("GET", "/api/v1/fraud-ring-candidates/{id}", f"/api/v1/fraud-ring-candidates/{pot}", 200)
    call("PATCH", "/api/v1/rings/{id}/status", f"{r}/status", 200, json={"status": "REVIEWED"})
    sim = call(
        "POST", "/api/v1/rings/{id}/interventions/simulate", f"{r}/interventions/simulate", 202, json={"mode": "RANK"}
    ).json()
    from tests.ingestutil import run_worker as _drain

    _drain(app, timeout=600)
    call("GET", "/api/v1/rings/{id}/interventions", f"{r}/interventions", 200)
    call("GET", "/api/v1/interventions/{id}", f"/api/v1/interventions/{sim['scenario_id']}", 200)
    call("GET", "/api/v1/interventions/{id}/candidates", f"/api/v1/interventions/{sim['scenario_id']}/candidates", 200)
    ev = call("POST", "/api/v1/evaluation/runs", "/api/v1/evaluation/runs", 202, json={}).json()
    _drain(app, timeout=600)
    call("GET", "/api/v1/evaluation/runs", "/api/v1/evaluation/runs", 200)
    call("GET", "/api/v1/evaluation/runs/{id}", f"/api/v1/evaluation/runs/{ev['evaluation_run_id']}", 200)
    call("GET", "/api/v1/evaluation/runs/{id}/{level}", f"/api/v1/evaluation/runs/{ev['evaluation_run_id']}/RING", 200)
    summary_alias = call("GET", "/api/v1/evaluation/summary", "/api/v1/evaluation/summary", 200)
    assert summary_alias.headers["deprecation"] == "true"
    call("GET", "/api/v1/evaluation/{level}", "/api/v1/evaluation/network", 200)
    from tests.copilotutil import install

    install(app)
    question = {"question": "Why is this account risky?", "account_id": acc}
    call("POST", "/api/v1/copilot/query", "/api/v1/copilot/query", 200, json=question)

    nb = call(
        "GET", "/api/v1/graph/neighborhood", "/api/v1/graph/neighborhood", 200, params={"account_id": acc, "depth": 2}
    ).json()
    dst = next(n["account_id"] for n in nb["nodes"] if n["hop"] == 1)
    call("GET", "/api/v1/graph/metrics", "/api/v1/graph/metrics", 200, params={"account_id": acc})
    params = {"source_account_id": acc, "destination_account_id": dst}
    path = call("GET", "/api/v1/graph/path", "/api/v1/graph/path", 200, params=params).json()
    alias = call("GET", "/api/v1/money-flow", "/api/v1/money-flow", 200, params=params)
    assert alias.headers["deprecation"] == "true" and "/api/v1/graph/path" in alias.headers["link"]
    assert {**alias.json(), "computed_at": None} == {**path, "computed_at": None}
    p0 = path["paths"][0]
    call(
        "GET",
        "/api/v1/graph/paths/{path_id}",
        f"/api/v1/graph/paths/{p0['path_id']}",
        200,
        params={"graph_snapshot_id": path["graph_snapshot_id"], "accounts": ",".join(p0["accounts"])},
    )
    communities = call("GET", "/api/v1/communities", "/api/v1/communities", 200).json()
    call("GET", "/api/v1/communities/{id}", f"/api/v1/communities/{communities['items'][0]['community_id']}", 200)

    case = new_case(client, admin)
    call.called.add(("POST", "/api/v1/cases"))
    validate("POST", "/api/v1/cases", 201, case)
    c = f"/api/v1/cases/{case['case_id']}"
    call("GET", "/api/v1/cases", "/api/v1/cases", 200)
    call("GET", "/api/v1/cases/{id}", c, 200)
    call("PATCH", "/api/v1/cases/{id}", c, 200, json={"version": 1, "priority": "LOW"})
    call(
        "POST", "/api/v1/cases/{id}/subjects", f"{c}/subjects", 201, json={"subject_type": "ACCOUNT", "subject_id": acc}
    )
    call("GET", "/api/v1/cases/{id}/subjects", f"{c}/subjects", 200)
    call("DELETE", "/api/v1/cases/{id}/subjects/{type}/{subject_id}", f"{c}/subjects/ACCOUNT/{acc}", 204)
    call(
        "POST",
        "/api/v1/cases/{id}/findings",
        f"{c}/findings",
        201,
        json={
            "type": "OBSERVATION",
            "description": "d",
            "evidence": [{"type": "account", "id": acc}],
            "source": "investigator",
        },
    )
    call("GET", "/api/v1/cases/{id}/findings", f"{c}/findings", 200)
    call("GET", "/api/v1/audit", "/api/v1/audit", 200, params={"action": "case.create"})

    # writes that start work come last: their pipelines change the active context
    resp = upload(client, admin, fixture_csv("abc_chain"), name="api-upload")
    assert resp.status_code == 202, resp.text
    validate("POST", "/api/v1/ingestion", 202, resp.json())
    call.called.add(("POST", "/api/v1/ingestion"))
    run_a, _ = _fail_at_graph_building(call, app, client, admin, "api-r1")
    call("POST", "/api/v1/pipeline-runs/{id}/retry", f"/api/v1/pipeline-runs/{run_a}/retry", 202)
    _run_b, ds_b = _fail_at_graph_building(call, app, client, admin, "api-r2")
    retried = call("POST", "/api/v1/ingestion/{id}/retry", f"/api/v1/ingestion/{ds_b.ingestion_run_id}/retry", 202)
    assert retried.headers["deprecation"] == "true" and "/retry" in retried.headers["link"]

    implemented = set(operations())
    assert call.called == implemented, sorted(implemented ^ call.called)
    srs = {(r.method, norm(r.path)): r.success for r in srs_rows()}
    for key in implemented:
        target = srs_aliases().get(key, key)
        assert key in srs or target in srs, key
