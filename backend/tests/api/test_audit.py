"""GET /audit (SRS §19.2, §24.3): ADMIN only, filters combine with AND, newest first, page ≤ 100."""

import pytest

from tests.caseutil import new_case
from tests.openapiutil import validate

pytestmark = pytest.mark.integration


def test_filters_and_order(client, users) -> None:
    admin = users("ADMIN")
    inv = users("INVESTIGATOR")
    c1 = new_case(client, inv)
    c2 = new_case(client, inv)
    client.get("/api/v1/audit", headers=inv.headers)  # DENIED event for the investigator
    url = "/api/v1/audit"
    body = client.get(url, params={"action": "case.create"}, headers=admin.headers).json()
    validate("GET", url, 200, body)
    assert [e["resource_id"] for e in body["items"]] == [c2["case_id"], c1["case_id"]]  # newest first
    mine = client.get(url, params={"user_id": str(inv.user_id), "outcome": "DENIED"}, headers=admin.headers).json()
    assert mine["total"] == 1 and mine["items"][0]["action"] == "authz.denied"
    assert mine["items"][0]["metadata"]["permission"] == "audit.read"
    one = client.get(url, params={"resource_type": "case", "resource_id": c1["case_id"]}, headers=admin.headers)
    assert [e["action"] for e in one.json()["items"]] == ["case.create"]
    rid = one.json()["items"][0]["request_id"]
    assert client.get(url, params={"request_id": rid}, headers=admin.headers).json()["total"] >= 1
    window = {"start": "2000-01-01T00:00:00Z", "end": "2000-01-02T00:00:00Z"}
    assert client.get(url, params=window, headers=admin.headers).json()["total"] == 0
    paged = client.get(url, params={"page_size": 1, "page": 2}, headers=admin.headers).json()
    assert len(paged["items"]) == 1 and paged["page"] == 2


@pytest.mark.parametrize(
    "params",
    [
        {"outcome": "MAYBE"},
        {"start": "not-a-time"},
        {"start": "2020-02-01T00:00:00Z", "end": "2020-01-01T00:00:00Z"},
        {"user_id": "nope"},
    ],
)
def test_invalid_filters(client, users, params) -> None:
    resp = client.get("/api/v1/audit", params=params, headers=users("ADMIN").headers)
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_no_question_text_or_secrets(client, users) -> None:
    admin = users("ADMIN")
    client.post("/api/v1/auth/login", json={"username": admin.username, "password": "wrong-password-123"})
    body = client.get("/api/v1/audit", params={"action": "auth.login"}, headers=admin.headers).json()
    assert body["items"] and "wrong-password-123" not in str(body)
