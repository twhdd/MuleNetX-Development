"""AuthService: login, sessions, users (SRS §22.1, §19.4)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mulenetx.audit.service import AuditService
from mulenetx.auth import sessions
from mulenetx.auth.passwords import Passwords, password_problem
from mulenetx.auth.permissions import ROLES
from mulenetx.auth.throttle import LOGIN_ACTION, is_throttled
from mulenetx.core import error_codes as ec
from mulenetx.core.config import Settings
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import PageRequest
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.auth import AuthSession, User


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    username: str
    role: str
    session_id: uuid.UUID


@dataclass(frozen=True)
class LoginResult:
    token: str
    expires_in: int
    user: User


def user_view(u: User) -> dict[str, Any]:
    return {
        "user_id": str(u.user_id),
        "username": u.username,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat(),
        "updated_at": u.updated_at.isoformat(),
        "last_login_at": None if u.last_login_at is None else u.last_login_at.isoformat(),
    }


class AuthService:
    def __init__(self, settings: Settings, audit: AuditService, passwords: Passwords) -> None:
        self.settings = settings
        self.audit = audit
        self.passwords = passwords
        self.policy = sessions.SessionPolicy.from_settings(settings)

    # ── login / logout / authenticate ──────────────────────────────────────

    def login(self, db: Session, username: str, password: str, client_ip: str) -> LoginResult:
        now = utcnow()
        meta = {"username": username[:100], "client_ip": client_ip}
        if is_throttled(
            db, username, client_ip, now, self.settings.login_max_failures, self.settings.login_window_minutes
        ):
            self.audit.record_now(LOGIN_ACTION, "auth_session", "DENIED", metadata={**meta, "reason": "THROTTLED"})
            raise AppError(ec.RATE_LIMITED, "Too many failed login attempts; try again later.")
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        valid = self.passwords.verify(None if user is None else user.password_hash, password)
        if user is None or not valid or not user.is_active:
            self.audit.record_now(
                LOGIN_ACTION,
                "auth_session",
                "FAILED",
                user_id=None if user is None else user.user_id,
                metadata=meta,
            )
            raise AppError(ec.INVALID_CREDENTIALS)
        token, row = sessions.create_session(db, user.user_id, user.role, self.policy, now)
        user.last_login_at = now
        self.audit.record_in(
            db,
            LOGIN_ACTION,
            "auth_session",
            "SUCCESS",
            user_id=user.user_id,
            resource_id=str(row.session_id),
            metadata=meta,
        )
        db.commit()
        return LoginResult(token=token, expires_in=int(self.policy.idle.total_seconds()), user=user)

    def authenticate(self, db: Session, token: str) -> Principal | None:
        """Validate a bearer token. Returns None for unknown, revoked, expired or inactive sessions."""
        if not token or len(token) > 256:
            return None
        now = utcnow()
        row = sessions.find_by_token(db, token)
        if row is None or row.revoked_at is not None:
            return None
        if now >= row.absolute_expires_at or now >= row.idle_expires_at:
            sessions.revoke(row, "EXPIRED", now)
            self.audit.record_in(
                db,
                "auth.session_revoked",
                "auth_session",
                "SUCCESS",
                user_id=row.user_id,
                resource_id=str(row.session_id),
                metadata={"reason": "EXPIRED"},
            )
            db.commit()
            return None
        user = db.get(User, row.user_id)
        if user is None or not user.is_active or user.role != row.role_at_issue:
            return None
        sessions.touch(row, self.policy, now)
        db.commit()
        return Principal(user_id=user.user_id, username=user.username, role=user.role, session_id=row.session_id)

    def logout(self, db: Session, principal: Principal) -> None:
        now = utcnow()
        row = db.get(AuthSession, principal.session_id)
        if row is not None:
            sessions.revoke(row, "LOGOUT", now)
        self.audit.record_in(
            db,
            "auth.logout",
            "auth_session",
            "SUCCESS",
            user_id=principal.user_id,
            resource_id=str(principal.session_id),
        )
        db.commit()

    # ── users ──────────────────────────────────────────────────────────────

    def list_users(self, db: Session, page: PageRequest) -> tuple[list[User], int]:
        total = int(db.execute(select(func.count()).select_from(User)).scalar_one())
        rows = db.execute(select(User).order_by(User.username).offset(page.offset).limit(page.page_size)).scalars()
        return list(rows), total

    def create_user(self, db: Session, actor: Principal, username: str, role: str, password: str) -> User:
        self._validate_role(role)
        self._validate_password(password)
        username = username.strip()
        if not username or len(username) > 100:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "username"})
        now = utcnow()
        user = User(
            user_id=uuid.uuid4(),
            username=username,
            password_hash=self.passwords.hash(password),
            role=role,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            raise AppError(ec.CONFLICT, "A user with this username already exists.", {"field": "username"}) from exc
        self.audit.record_in(
            db,
            "user.create",
            "user",
            "SUCCESS",
            user_id=actor.user_id,
            resource_id=str(user.user_id),
            metadata={"role": role},
        )
        db.commit()
        return user

    def update_user(
        self,
        db: Session,
        actor: Principal,
        user_id: uuid.UUID,
        *,
        role: str | None,
        is_active: bool | None,
        password: str | None,
    ) -> User:
        user = db.get(User, user_id, with_for_update=True)
        if user is None:
            raise AppError(ec.NOT_FOUND, details={"resource": "user"})
        now = utcnow()
        changed = False
        if role is not None and role != user.role:
            self._validate_role(role)
            old = user.role
            user.role = role
            revoked = sessions.revoke_all_for_user(db, user.user_id, "ROLE_CHANGED", now)
            self.audit.record_in(
                db,
                "user.role_change",
                "user",
                "SUCCESS",
                user_id=actor.user_id,
                resource_id=str(user.user_id),
                metadata={"from": old, "to": role, "sessions_revoked": revoked},
            )
            changed = True
        if is_active is not None and is_active != user.is_active:
            user.is_active = is_active
            action = "user.activate" if is_active else "user.deactivate"
            meta: dict[str, Any] = {}
            if not is_active:
                meta["sessions_revoked"] = sessions.revoke_all_for_user(db, user.user_id, "DEACTIVATED", now)
            self.audit.record_in(
                db, action, "user", "SUCCESS", user_id=actor.user_id, resource_id=str(user.user_id), metadata=meta
            )
            changed = True
        if password is not None:
            self._validate_password(password)
            user.password_hash = self.passwords.hash(password)
            self.audit.record_in(
                db, "user.password_change", "user", "SUCCESS", user_id=actor.user_id, resource_id=str(user.user_id)
            )
            changed = True
        if changed:
            user.updated_at = now
        db.commit()
        return user

    def bootstrap_admin(self, db: Session, username: str, password: str) -> User:
        exists = db.execute(select(func.count()).select_from(User).where(User.role == "ADMIN")).scalar_one()
        if exists:
            raise AppError(ec.CONFLICT, "An administrator already exists; bootstrap refused.")
        self._validate_password(password)
        now = utcnow()
        user = User(
            user_id=uuid.uuid4(),
            username=username,
            password_hash=self.passwords.hash(password),
            role="ADMIN",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        db.flush()
        self.audit.record_in(db, "user.bootstrap_admin", "user", "SUCCESS", resource_id=str(user.user_id))
        db.commit()
        return user

    @staticmethod
    def _validate_role(role: str) -> None:
        if role not in ROLES:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "role"})

    @staticmethod
    def _validate_password(password: str) -> None:
        problem = password_problem(password)
        if problem is not None:
            raise AppError(ec.VALIDATION_ERROR, problem, details={"field": "password"})
