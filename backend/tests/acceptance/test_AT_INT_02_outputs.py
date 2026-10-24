"""AT-INT-02: every candidate reports the §16A.15 outputs; scenario and candidates are labelled hypothetical and
carry the baseline truncation state; results are only served once COMPLETED."""

import pytest

from tests.openapiutil import validate
from tests.scenarioutil import complete, potential_ring, simulate

pytestmark = pytest.mark.integration


def test_AT_INT_02_outputs(app, client, users) -> None:
    ring = potential_ring(app, client, users("ADMIN"), "i2")
    inv = users("INVESTIGATOR")
    accepted = simulate(client, inv, ring["ring_id"], {"mode": "RANK"})
    validate("POST", "/api/v1/rings/{id}/interventions/simulate", 202, accepted.json())
    sid = accepted.json()["scenario_id"]
    assert accepted.json() == {"scenario_id": sid, "status": "QUEUED", "hypothetical": True}
    early = client.get(f"/api/v1/interventions/{sid}/candidates", headers=inv.headers)
    assert early.status_code == 409 and early.json()["error"]["code"] == "SCENARIO_NOT_COMPLETED"

    scenario = complete(app, client, inv, sid)
    validate("GET", "/api/v1/interventions/{id}", 200, scenario)
    assert scenario["hypothetical"] is True and "No account" in scenario["statement"]
    assert scenario["baseline"]["suspicious_paths"] > 0 and scenario["baseline"]["network_risk"] == 1.0
    assert scenario["eligible_candidate_count"] > 0 and len(scenario["ranking_configuration_hash"]) == 64
    page = client.get(f"/api/v1/interventions/{sid}/candidates", params={"page_size": 100}, headers=inv.headers).json()
    validate("GET", "/api/v1/interventions/{id}/candidates", 200, page)
    assert page["hypothetical"] is True and page["total"] == scenario["eligible_candidate_count"]
    first = page["items"]
    assert [c["rank_position"] for c in first] == list(range(1, len(first) + 1))
    scores = [c["intervention_score"] for c in first]
    assert scores == sorted(scores, reverse=True)
    for c in first:
        assert c["hypothetical"] is True and c["baseline_paths_truncated"] == scenario["baseline_paths_truncated"]
        assert c["operation_type"] != "ACCOUNT_SET_REMOVAL"  # never generated in RANK
        assert 0 <= c["flow_disruption_percentage"] <= 1 and 0 <= c["normalized_risk_reduction"] <= 1
        assert c["intervention_cost"] == 1 and abs(c["normalized_intervention_cost"] - 0.3333333) < 1e-9
        assert c["evidence"]["hypothetical"] is True
    listed = client.get(f"/api/v1/rings/{ring['ring_id']}/interventions", headers=inv.headers).json()
    validate("GET", "/api/v1/rings/{id}/interventions", 200, listed)
    assert [s["scenario_id"] for s in listed["items"]] == [sid]

    # EVALUATE the top RANK candidate: same metrics, rank 1
    top = first[0]
    body = {"mode": "EVALUATE", "intervention_type": top["operation_type"], "target_ids": top["target_ids"]}
    ev = simulate(client, inv, ring["ring_id"], body)
    assert ev.status_code == 202, ev.text
    complete(app, client, inv, ev.json()["scenario_id"])
    (only,) = client.get(f"/api/v1/interventions/{ev.json()['scenario_id']}/candidates", headers=inv.headers).json()[
        "items"
    ]
    # same baseline, run, ring, operation, targets and ranking configuration → the same candidate ID (§6.2.3)
    assert only["rank_position"] == 1 and only["candidate_id"] == top["candidate_id"]
    for k in ("flow_disruption_percentage", "normalized_risk_reduction", "intervention_score"):
        assert only[k] == top[k]
