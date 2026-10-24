"""AT-EVAL-03: the report shows the transaction → account → ring → network progression and states that PaySim
has no authoritative mule-ring ground truth; labels it cannot provide are NOT_MEASURABLE, not 0. Also the
evaluation aliases and error states."""

import pytest

from tests.evalutil import evaluate, metric, seed_with_ring

pytestmark = pytest.mark.integration


def test_AT_EVAL_03_progression_and_limitation(app, client, users) -> None:
    admin = users("ADMIN")
    h = admin.headers
    none = client.get("/api/v1/evaluation/summary", headers=h)
    assert none.status_code == 404 and none.json()["error"]["code"] == "EVALUATION_NOT_AVAILABLE"
    seed_with_ring(app, client, admin, "e3")
    s = evaluate(app, client, admin)
    assert [p["level"] for p in s["progression"]] == ["TRANSACTION", "ACCOUNT", "RING", "NETWORK"]
    assert all(p["value"] is not None for p in s["progression"])
    assert "no authoritative mule-account or mule-ring ground truth" in s["limitation"]
    for lvl, name in (("ACCOUNT", "mule_account_identity"), ("RING", "ring_identity_ground_truth")):
        m = metric(s, lvl, name)
        assert m["state"] == "NOT_MEASURABLE" and m["value"] is None and m["details"]["reason"]

    alias = client.get("/api/v1/evaluation/summary", headers=h)
    assert alias.headers["deprecation"] == "true" and s["evaluation_run_id"] in alias.headers["link"]
    assert alias.json()["evaluation_run_id"] == s["evaluation_run_id"]
    ring_alias = client.get("/api/v1/evaluation/ring", headers=h)
    assert ring_alias.headers["deprecation"] == "true" and ring_alias.json()["level"] == "RING"
    assert client.get(f"/api/v1/evaluation/runs/{s['evaluation_run_id']}/WHOLE", headers=h).status_code == 400
    queued = client.post("/api/v1/evaluation/runs", json={}, headers=h).json()["evaluation_run_id"]
    pending = client.get(f"/api/v1/evaluation/runs/{queued}/RING", headers=h)
    assert pending.status_code == 409
    analyst = users("ANALYST")
    assert client.post("/api/v1/evaluation/runs", json={}, headers=analyst.headers).status_code == 403
    assert client.get("/api/v1/evaluation/runs", headers=analyst.headers).status_code == 200
