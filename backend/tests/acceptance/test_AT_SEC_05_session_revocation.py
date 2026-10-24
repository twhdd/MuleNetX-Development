"""AT-SEC-05 / SR-21: after deactivation, role change or logout, reusing the token returns 401."""

import pytest

from tests.apiutil import audit_events

pytestmark = pytest.mark.integration


def test_AT_SEC_05_deactivation_revokes(app, client, users) -> None:
    admin = users("ADMIN")
    victim = users("INVESTIGATOR")
    assert client.get("/api/v1/auth/me", headers=victim.headers).status_code == 200
    resp = client.patch(f"/api/v1/users/{victim.user_id}", json={"is_active": False}, headers=admin.headers)
    assert resp.status_code == 200
    assert client.get("/api/v1/auth/me", headers=victim.headers).status_code == 401
    assert any(e.action == "user.deactivate" for e in audit_events(app))


def test_AT_SEC_05_role_change_revokes(client, users) -> None:
    admin = users("ADMIN")
    victim = users("INVESTIGATOR")
    resp = client.patch(f"/api/v1/users/{victim.user_id}", json={"role": "ANALYST"}, headers=admin.headers)
    assert resp.status_code == 200
    assert client.get("/api/v1/auth/me", headers=victim.headers).status_code == 401


def test_AT_SEC_05_logout_revokes(client, users) -> None:
    victim = users("ANALYST")
    assert client.post("/api/v1/auth/logout", headers=victim.headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=victim.headers).status_code == 401
