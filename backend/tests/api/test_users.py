"""User administration API (SRS §19.2, §22.1)."""

import pytest

from tests.apiutil import audit_events

pytestmark = pytest.mark.integration


def test_create_list_and_patch(app, client, users) -> None:
    admin = users("ADMIN")
    created = client.post(
        "/api/v1/users",
        json={"username": "new.analyst", "role": "ANALYST", "password": "a-long-password"},
        headers=admin.headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["role"] == "ANALYST" and body["is_active"] is True and "password_hash" not in body
    listed = client.get("/api/v1/users", params={"page_size": 100}, headers=admin.headers).json()
    assert {"items", "page", "page_size", "total", "total_is_capped"} == set(listed)
    assert "new.analyst" in [u["username"] for u in listed["items"]]
    patched = client.patch(f"/api/v1/users/{body['user_id']}", json={"role": "INVESTIGATOR"}, headers=admin.headers)
    assert patched.status_code == 200 and patched.json()["role"] == "INVESTIGATOR"
    actions = [e.action for e in audit_events(app)]
    assert "user.create" in actions and "user.role_change" in actions


def test_duplicate_username_409(client, users) -> None:
    admin = users("ADMIN")
    payload = {"username": "dup.user", "role": "ANALYST", "password": "a-long-password"}
    assert client.post("/api/v1/users", json=payload, headers=admin.headers).status_code == 201
    dup = client.post("/api/v1/users", json=payload, headers=admin.headers)
    assert dup.status_code == 409


def test_validation(client, users) -> None:
    admin = users("ADMIN")
    bad_role = client.post(
        "/api/v1/users", json={"username": "u", "role": "ROOT", "password": "a-long-password"}, headers=admin.headers
    )
    short_pw = client.post(
        "/api/v1/users", json={"username": "u", "role": "ANALYST", "password": "short"}, headers=admin.headers
    )
    assert bad_role.status_code == 400 and short_pw.status_code == 400
    assert short_pw.json()["error"]["details"] == {"field": "password"}


def test_page_size_limit(client, users) -> None:
    admin = users("ADMIN")
    resp = client.get("/api/v1/users", params={"page_size": 101}, headers=admin.headers)
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "LIMIT_EXCEEDED"


def test_patch_unknown_user_404(client, users) -> None:
    admin = users("ADMIN")
    resp = client.patch(
        "/api/v1/users/00000000-0000-4000-8000-000000000001", json={"is_active": False}, headers=admin.headers
    )
    assert resp.status_code == 404


def test_non_admin_denied_and_audited(app, client, users) -> None:
    analyst = users("ANALYST")
    resp = client.get("/api/v1/users", headers=analyst.headers)
    assert resp.status_code == 403 and resp.json()["error"]["code"] == "FORBIDDEN"
    denied = audit_events(app, "authz.denied", "DENIED")
    assert denied and denied[-1].metadata_["permission"] == "user.read"
