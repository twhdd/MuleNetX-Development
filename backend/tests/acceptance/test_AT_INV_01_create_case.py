"""AT-INV-01: an investigator creates a case: status OPEN, version 1, created_by the principal, audit event."""

import pytest

from tests.apiutil import audit_events
from tests.caseutil import new_case

pytestmark = pytest.mark.integration


def test_AT_INV_01_create_case(app, client, users) -> None:
    inv = users("INVESTIGATOR")
    case = new_case(client, inv)
    assert case["status"] == "OPEN" and case["version"] == 1 and case["created_by"] == str(inv.user_id)
    events = audit_events(app, "case.create", "SUCCESS")
    assert events and events[-1].resource_id == case["case_id"] and events[-1].user_id == inv.user_id
    assert client.get(f"/api/v1/cases/{case['case_id']}", headers=inv.headers).json() == case
    forced = client.post(
        "/api/v1/cases", json={"title": "x", "priority": "LOW", "status": "CLOSED"}, headers=inv.headers
    )
    assert forced.status_code == 400  # status is always OPEN on creation
