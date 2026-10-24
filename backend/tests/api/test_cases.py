"""Case API: findings validation, listing, filters (SRS §17.5, §19.2)."""

import pytest

from tests.caseutil import new_case, patch
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def test_findings(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("CA", "CB", 1.0, 1)], key="fd")
    inv = users("INVESTIGATOR")
    case = new_case(client, inv)
    url = f"/api/v1/cases/{case['case_id']}/findings"
    ok = client.post(
        url,
        json={
            "type": "OBSERVATION",
            "description": "Rapid pass-through observed.",
            "evidence": [{"type": "account", "id": "fd:CA"}, {"type": "transaction", "id": "fd:0000000001"}],
            "source": "investigator",
        },
        headers=inv.headers,
    )
    assert ok.status_code == 201 and ok.json()["label"] == "INVESTIGATOR FINDING"
    bad = client.post(
        url,
        json={
            "type": "OBSERVATION",
            "description": "x",
            "evidence": [{"type": "account", "id": "no"}],
            "source": "investigator",
        },
        headers=inv.headers,
    )
    assert bad.status_code == 400 and bad.json()["error"]["details"] == {"field": "evidence.0"}
    huge = client.post(
        url, json={"type": "OBS", "description": "x" * 20001, "evidence": [], "source": "s"}, headers=inv.headers
    )
    assert huge.status_code in (400, 413)
    listing = client.get(url, headers=inv.headers).json()
    assert listing["total"] == 1 and listing["items"][0]["evidence"][0] == {"type": "account", "id": "fd:CA"}
    outsider = users("ANALYST")
    assert (
        client.post(
            url, json={"type": "OBS", "description": "x", "evidence": [], "source": "s"}, headers=outsider.headers
        ).status_code
        == 403
    )
    case = client.get(f"/api/v1/cases/{case['case_id']}", headers=inv.headers).json()
    case = patch(client, inv, case, status="IN_REVIEW").json()
    case = patch(client, inv, case, status="RESOLVED").json()
    patch(client, inv, case, status="CLOSED")
    assert (
        client.post(
            url, json={"type": "OBS", "description": "x", "evidence": [], "source": "s"}, headers=inv.headers
        ).status_code
        == 409
    )


def test_list_and_filters(client, users) -> None:
    inv = users("INVESTIGATOR")
    new_case(client, inv)
    c2 = new_case(client, inv, assigned_to=str(inv.user_id))
    analyst = users("ANALYST")
    all_cases = client.get("/api/v1/cases", headers=analyst.headers).json()
    assert all_cases["total"] == 2  # every role reads every case
    mine = client.get("/api/v1/cases", params={"assigned_to": str(inv.user_id)}, headers=analyst.headers).json()
    assert [c["case_id"] for c in mine["items"]] == [c2["case_id"]]
    assert client.get("/api/v1/cases", params={"status": "NOPE"}, headers=analyst.headers).status_code == 400
    assert client.get("/api/v1/cases/00000000-0000-4000-8000-000000000001", headers=analyst.headers).status_code == 404
    denied = client.post(
        "/api/v1/cases",
        json={"title": "x", "priority": "LOW", "assigned_to": str(inv.user_id)},
        headers=analyst.headers,
    )
    assert denied.status_code == 403  # ANALYST may not assign
