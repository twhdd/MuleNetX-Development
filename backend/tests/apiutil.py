"""API test helpers."""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from mulenetx.api.deps import get_services
from mulenetx.auth.service import Principal
from mulenetx.db.models.audit import AuditEvent
from mulenetx.db.models.auth import User

_N = itertools.count(1)
PASSWORD = "correct-horse-battery"


@dataclass
class Actor:
    user_id: uuid.UUID
    username: str
    role: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


class _Req:
    def __init__(self, app: FastAPI) -> None:
        self.app = app


class UserFactory:
    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.services = get_services(_Req(app))  # type: ignore[arg-type]
        self.client = TestClient(app)

    def create(self, role: str, password: str = PASSWORD, username: str | None = None) -> User:
        name = username or f"{role.lower()}{next(_N)}"
        system = Principal(user_id=uuid.uuid4(), username="system", role="ADMIN", session_id=uuid.uuid4())
        with self.services.runtime.session_factory() as db:
            db.add(
                User(
                    user_id=system.user_id,
                    username=f"system{next(_N)}",
                    password_hash="x",
                    role="ADMIN",
                    is_active=False,
                    created_at=_now(),
                    updated_at=_now(),
                )
            )
            db.commit()
            return self.services.auth.create_user(db, system, name, role, password)

    def __call__(self, role: str) -> Actor:
        user = self.create(role)
        token = self.login(user.username, PASSWORD)
        return Actor(user.user_id, user.username, role, token)

    def login(self, username: str, password: str) -> str:
        resp = self.client.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        token: str = resp.json()["access_token"]
        return token


def _now() -> Any:
    from mulenetx.core.timeutil import utcnow

    return utcnow()


def audit_events(app: FastAPI, action: str | None = None, outcome: str | None = None) -> list[AuditEvent]:
    services = get_services(_Req(app))  # type: ignore[arg-type]
    with services.runtime.session_factory() as db:
        q = select(AuditEvent).order_by(AuditEvent.timestamp)
        if action is not None:
            q = q.where(AuditEvent.action == action)
        if outcome is not None:
            q = q.where(AuditEvent.outcome == outcome)
        return list(db.execute(q).scalars())
