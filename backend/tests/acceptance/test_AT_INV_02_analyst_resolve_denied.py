"""AT-INV-02: an analyst cannot resolve a case (403, audited), even as its participant."""

import pytest

from tests.apiutil import audit_events
from tests.caseutil import new_case, patch

pytestmark = pytest.mark.integration


def test_AT_INV_02_analyst_resolve_denied(app, client, users) -> None:
    analyst = users("ANALYST")
    case = new_case(client, analyst)
    case = patch(client, analyst, case, status="IN_REVIEW").json()  # participant may move OPEN → IN_REVIEW
    assert case["status"] == "IN_REVIEW"
    for target in ("RESOLVED", "FALSE_POSITIVE"):
        resp = patch(client, analyst, case, status=target)
        assert resp.status_code == 403 and resp.json()["error"]["code"] == "FORBIDDEN"
    denied = audit_events(app, "authz.denied", "DENIED")
    assert denied[-1].user_id == analyst.user_id and denied[-1].resource_id == case["case_id"]
    inv = users("INVESTIGATOR")
    assert patch(client, inv, case, status="RESOLVED").status_code == 200
