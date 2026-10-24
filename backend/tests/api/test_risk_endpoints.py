"""Risk, propagation, features and temporal endpoints (SRS §19.2, §19.7, §19.12, §15.8)."""

import pytest

from tests.ingestutil import seed_synth_and_activate

pytestmark = pytest.mark.integration


def test_risk_endpoints(app, client, users) -> None:
    admin = users("ADMIN")
    _ds, run = seed_synth_and_activate(app, client, admin, key="re")
    analyst = users("ANALYST")
    account = "re:C90000"  # the first mule
    risk = client.get(f"/api/v1/accounts/{account}/risk", headers=analyst.headers)
    assert risk.status_code == 200, risk.text
    body = risk.json()
    for key in (
        "ml_score",
        "graph_signal_score",
        "behavioral_signal_score",
        "rule_signal_score",
        "pre_propagation_score",
        "propagated_risk",
        "final_score",
        "risk_tier",
        "signal_availability",
        "fired_rules",
        "signal_coverage",
        "max_attainable_score",
        "lineage",
        "computed_at",
        "is_stale",
    ):
        assert key in body, key
    assert body["is_stale"] is False and body["lineage"]["scoring_run_id"] == run["scoring_run_id"]
    assert body["signal_availability"]["ml"]["state"] == "AVAILABLE"
    assert 0 <= body["final_score"] <= 0.95
    assert body["signal_coverage"] == 1.0
    assert body["max_attainable_score"] >= body["final_score"]

    prop = client.get(f"/api/v1/accounts/{account}/risk/propagation", headers=analyst.headers).json()
    assert prop["propagated_risk"] == body["propagated_risk"]
    assert len(prop["contributions"]) <= 5
    if prop["contributions"]:
        assert prop["contributions"][0]["rank"] == 1
        assert prop["contributions"][0]["contribution"] == body["propagated_risk"]

    feats = client.get(f"/api/v1/accounts/{account}/features", headers=analyst.headers).json()
    assert len(feats["features"]) == 42 and feats["feature_version"] == "v1"
    assert {f["state"] for f in feats["features"]} <= {"OBSERVED", "ZERO", "UNAVAILABLE", "NOT_APPLICABLE"}
    temporal = client.get(f"/api/v1/accounts/{account}/temporal", headers=analyst.headers).json()
    assert [f["feature_id"] for f in temporal["features"]] == [f"F{i}" for i in range(21, 31)]
    assert temporal["cutoff"] and temporal["lineage"]["scoring_run_id"] == run["scoring_run_id"]

    missing = client.get(
        f"/api/v1/accounts/{account}/risk",
        params={"scoring_run_id": "00000000-0000-4000-8000-000000000001"},
        headers=analyst.headers,
    )
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "RISK_NOT_AVAILABLE"
    assert client.get("/api/v1/accounts/re:NOPE/risk", headers=analyst.headers).status_code == 404


def test_risk_not_available_without_scoring(client, users) -> None:
    analyst = users("ANALYST")
    assert client.get("/api/v1/accounts/x:Y/risk", headers=analyst.headers).status_code == 404
