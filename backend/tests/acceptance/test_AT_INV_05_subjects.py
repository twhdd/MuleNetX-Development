"""AT-INV-05: subjects are linked after an existence check; removal is soft and audited; history kept."""

import pytest

from tests.apiutil import audit_events
from tests.caseutil import new_case, patch
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def test_AT_INV_05_subjects(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("CA", "CB", 1.0, 1)], key="sub")
    inv = users("INVESTIGATOR")
    case = new_case(client, inv)
    url = f"/api/v1/cases/{case['case_id']}/subjects"
    added = client.post(url, json={"subject_type": "ACCOUNT", "subject_id": "sub:CA"}, headers=inv.headers)
    assert added.status_code == 201 and added.json()["active"] is True
    tx = client.post(url, json={"subject_type": "TRANSACTION", "subject_id": "sub:0000000001"}, headers=inv.headers)
    assert tx.status_code == 201
    dup = client.post(url, json={"subject_type": "ACCOUNT", "subject_id": "sub:CA"}, headers=inv.headers)
    assert dup.status_code == 409
    missing = client.post(url, json={"subject_type": "ACCOUNT", "subject_id": "sub:NOPE"}, headers=inv.headers)
    assert missing.status_code == 404
    ring = client.post(url, json={"subject_type": "RING", "subject_id": "not-a-uuid"}, headers=inv.headers)
    assert ring.status_code == 404
    assert client.delete(f"{url}/ACCOUNT/sub:CA", headers=inv.headers).status_code == 204
    assert client.delete(f"{url}/ACCOUNT/sub:CA", headers=inv.headers).status_code == 404
    listing = client.get(url, headers=inv.headers).json()
    ca = [s for s in listing["items"] if s["subject_id"] == "sub:CA"]
    assert len(ca) == 1 and ca[0]["active"] is False and ca[0]["removed_by"] == str(inv.user_id)
    assert (
        client.post(url, json={"subject_type": "ACCOUNT", "subject_id": "sub:CA"}, headers=inv.headers).status_code
        == 201
    )
    actions = [e.action for e in audit_events(app)]
    assert actions.count("case_subject.add") == 3 and actions.count("case_subject.remove") == 1
    case = client.get(f"/api/v1/cases/{case['case_id']}", headers=inv.headers).json()
    case = patch(client, inv, case, status="IN_REVIEW").json()
    case = patch(client, inv, case, status="RESOLVED").json()
    patch(client, inv, case, status="CLOSED")
    closed = client.post(url, json={"subject_type": "ACCOUNT", "subject_id": "sub:CB"}, headers=inv.headers)
    assert closed.status_code == 409
