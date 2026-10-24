"""AT-SEC-02: an ANALYST calling the audit endpoint receives 403 and no audit data; the denial is audited."""

import pytest

from tests.apiutil import audit_events

pytestmark = pytest.mark.integration


def test_AT_SEC_02_analyst_cannot_read_audit(app, client, users) -> None:
    analyst = users("ANALYST")
    resp = client.get("/api/v1/audit", headers=analyst.headers)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert set(body) == {"error"} and "items" not in body["error"]["details"]
    denied = audit_events(app, "authz.denied", "DENIED")
    assert denied[-1].user_id == analyst.user_id and denied[-1].metadata_["permission"] == "audit.read"
    assert client.get("/api/v1/audit", headers=users("INVESTIGATOR").headers).status_code == 403
    assert client.get("/api/v1/audit", headers=users("ADMIN").headers).status_code == 200
