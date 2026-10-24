"""AT-INV-03: an invalid transition returns 409 INVALID_CASE_TRANSITION."""

import pytest

from tests.caseutil import new_case, patch

pytestmark = pytest.mark.integration


def test_AT_INV_03_invalid_transition(client, users) -> None:
    inv = users("INVESTIGATOR")
    case = new_case(client, inv)
    for target in ("RESOLVED", "CLOSED", "ESCALATED", "FALSE_POSITIVE"):
        resp = patch(client, inv, case, status=target)
        assert resp.status_code == 409 and resp.json()["error"]["code"] == "INVALID_CASE_TRANSITION", target
    case = patch(client, inv, case, status="IN_REVIEW").json()
    case = patch(client, inv, case, status="FALSE_POSITIVE").json()
    case = patch(client, inv, case, status="CLOSED").json()
    assert case["status"] == "CLOSED" and case["closed_at"] is not None
    assert patch(client, inv, case, title="renamed").status_code == 409  # closed cases are immutable
