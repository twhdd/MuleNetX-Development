"""AT-RING-05: an ANALYST cannot change a ring's review status (403, audited); an INVESTIGATOR can (200, audited);
transitions follow §9.4; status never changes a score."""

import pytest

from tests.apiutil import audit_events
from tests.ringapi import rings_by_class

pytestmark = pytest.mark.integration


def test_AT_RING_05_status_permissions(app, client, users) -> None:
    ring = rings_by_class(app, client, users("ADMIN"), "r5")["POTENTIAL_FRAUD_RING_CANDIDATE"]
    url = f"/api/v1/rings/{ring['ring_id']}/status"
    analyst = users("ANALYST")
    denied = client.patch(url, json={"status": "REVIEWED"}, headers=analyst.headers)
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "FORBIDDEN"
    d = audit_events(app, "authz.denied", "DENIED")[-1]
    assert d.user_id == analyst.user_id and d.metadata_["permission"] == "ring.review"

    inv = users("INVESTIGATOR")
    ok = client.patch(url, json={"status": "REVIEWED"}, headers=inv.headers)
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["candidate_status"] == "REVIEWED" and body["status_changed_by"] == str(inv.user_id)
    assert body["candidate_score"] == ring["candidate_score"] and body["ring_risk_score"] == ring["ring_risk_score"]
    event = audit_events(app, "ring.status", "SUCCESS")[-1]
    assert event.resource_id == ring["ring_id"] and event.metadata_ == {"from": "CANDIDATE", "to": "REVIEWED"}

    assert (
        client.patch(url, json={"status": "DISMISSED"}, headers=inv.headers).json()["candidate_status"] == "DISMISSED"
    )
    assert (
        client.patch(url, json={"status": "REVIEWED"}, headers=inv.headers).status_code == 200
    )  # REVIEWED ↔ DISMISSED
    back = client.patch(url, json={"status": "CANDIDATE"}, headers=inv.headers)
    assert back.status_code == 409  # no transition back to CANDIDATE
    bad = client.patch(url, json={"status": "CONFIRMED"}, headers=inv.headers)
    assert bad.status_code == 400
    missing = client.patch(
        "/api/v1/rings/00000000-0000-4000-8000-000000000000/status", json={"status": "REVIEWED"}, headers=inv.headers
    )
    assert missing.status_code == 404
