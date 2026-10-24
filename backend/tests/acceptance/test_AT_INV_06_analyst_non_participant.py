"""AT-INV-06: an analyst who is not a participant cannot change a case's title (403); participants can."""

import pytest

from tests.caseutil import new_case, patch

pytestmark = pytest.mark.integration


def test_AT_INV_06_analyst_non_participant(client, users) -> None:
    inv = users("INVESTIGATOR")
    outsider = users("ANALYST")
    case = new_case(client, inv)
    resp = patch(client, outsider, case, title="hijacked")
    assert resp.status_code == 403
    for field, value in (("priority", "LOW"), ("status", "IN_REVIEW")):
        assert patch(client, outsider, case, **{field: value}).status_code == 403
    assert patch(client, outsider, case, assigned_to=str(outsider.user_id)).status_code == 403
    # once assigned (by an investigator), the analyst is a participant for title/priority/OPEN → IN_REVIEW
    case = patch(client, inv, case, assigned_to=str(outsider.user_id)).json()
    case = patch(client, outsider, case, title="Analyst's working title").json()
    assert case["title"] == "Analyst's working title"
    sub = client.post(
        f"/api/v1/cases/{case['case_id']}/subjects",
        json={"subject_type": "ACCOUNT", "subject_id": "x"},
        headers=users("ANALYST").headers,
    )
    assert sub.status_code == 403  # case_subject.manage is participant-only for ANALYST
