"""Authentication API (SRS §19.4, §22.1)."""

from datetime import timedelta

import pytest
from sqlalchemy import update

from mulenetx.api.deps import get_services
from mulenetx.auth.sessions import token_hash
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.auth import AuthSession
from tests.apiutil import PASSWORD, _Req, audit_events

pytestmark = pytest.mark.integration


def test_login_contract(client, users) -> None:
    user = users.create("INVESTIGATOR")
    resp = client.post("/api/v1/auth/login", json={"username": user.username, "password": PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"access_token", "token_type", "expires_in", "user"}
    assert body["token_type"] == "bearer" and body["expires_in"] == 1800
    assert body["user"] == {"user_id": str(user.user_id), "username": user.username, "role": "INVESTIGATOR"}
    assert len(body["access_token"]) >= 43


def test_token_is_stored_hashed_only(app, client, users) -> None:
    actor = users("ANALYST")
    services = get_services(_Req(app))
    with services.runtime.session_factory() as db:
        rows = db.query(AuthSession).filter(AuthSession.user_id == actor.user_id).all()
    assert rows and all(r.token_hash == token_hash(actor.token) for r in rows)
    assert all(actor.token not in r.token_hash for r in rows)


def test_generic_401_for_wrong_password_unknown_user_and_inactive(client, users) -> None:
    user = users.create("ANALYST")
    wrong = client.post("/api/v1/auth/login", json={"username": user.username, "password": "wrong-password-x"})
    unknown = client.post("/api/v1/auth/login", json={"username": "nobody-here", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["code"] == unknown.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]

    admin = users("ADMIN")
    client.patch(f"/api/v1/users/{user.user_id}", json={"is_active": False}, headers=admin.headers)
    inactive = client.post("/api/v1/auth/login", json={"username": user.username, "password": PASSWORD})
    assert inactive.status_code == 401
    assert inactive.json()["error"] == {**wrong.json()["error"], "request_id": inactive.json()["error"]["request_id"]}


def test_login_audited(app, client, users) -> None:
    user = users.create("ANALYST")
    client.post("/api/v1/auth/login", json={"username": user.username, "password": PASSWORD})
    client.post("/api/v1/auth/login", json={"username": user.username, "password": "bad-password-x"})
    events = audit_events(app, "auth.login")
    assert [e.outcome for e in events][-2:] == ["SUCCESS", "FAILED"]
    assert all("password" not in (e.metadata_ or {}) for e in events)


def test_throttling_per_username(client, users) -> None:
    user = users.create("ANALYST")
    for _ in range(5):
        r = client.post("/api/v1/auth/login", json={"username": user.username, "password": "bad-password-x"})
        assert r.status_code == 401
    blocked = client.post("/api/v1/auth/login", json={"username": user.username, "password": PASSWORD})
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"


def test_throttling_per_client_ip(client, users) -> None:
    for i in range(5):
        client.post("/api/v1/auth/login", json={"username": f"ghost{i}", "password": "bad-password-x"})
    user = users.create("ANALYST")
    blocked = client.post("/api/v1/auth/login", json={"username": user.username, "password": PASSWORD})
    assert blocked.status_code == 429


def test_logout_revokes_session(client, users) -> None:
    actor = users("ANALYST")
    assert client.get("/api/v1/auth/me", headers=actor.headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=actor.headers).status_code == 204
    after = client.get("/api/v1/auth/me", headers=actor.headers)
    assert after.status_code == 401
    assert after.json()["error"]["code"] == "UNAUTHENTICATED"


def test_me(client, users) -> None:
    actor = users("INVESTIGATOR")
    body = client.get("/api/v1/auth/me", headers=actor.headers).json()
    assert body["username"] == actor.username and body["role"] == "INVESTIGATOR"
    assert "password_hash" not in body


def test_idle_expiry(app, client, users) -> None:
    actor = users("ANALYST")
    services = get_services(_Req(app))
    with services.runtime.session_factory() as db:
        db.execute(
            update(AuthSession)
            .where(AuthSession.token_hash == token_hash(actor.token))
            .values(idle_expires_at=utcnow() - timedelta(seconds=1))
        )
        db.commit()
    assert client.get("/api/v1/auth/me", headers=actor.headers).status_code == 401


def test_sliding_idle_renewal(app, client, users) -> None:
    actor = users("ANALYST")
    services = get_services(_Req(app))
    with services.runtime.session_factory() as db:
        before = db.query(AuthSession).filter(AuthSession.token_hash == token_hash(actor.token)).one().idle_expires_at
    client.get("/api/v1/auth/me", headers=actor.headers)
    with services.runtime.session_factory() as db:
        after = db.query(AuthSession).filter(AuthSession.token_hash == token_hash(actor.token)).one().idle_expires_at
    assert after >= before


def test_login_body_limit(client) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        content=b'{"username":"' + b"a" * 5000 + b'"}',
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 413


def test_login_validation(client) -> None:
    assert client.post("/api/v1/auth/login", json={"username": "x"}).status_code == 400
