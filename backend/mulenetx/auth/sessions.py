"""Opaque bearer sessions (SRS §22.1): 256-bit token, SHA-256 hash stored, idle 30 min sliding,
absolute 12 h. The plaintext token is never stored or logged."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from mulenetx.core.config import Settings
from mulenetx.db.models.auth import AuthSession


def new_token() -> str:
    return secrets.token_urlsafe(32)  # 32 bytes = 256 bits, base64url


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SessionPolicy:
    idle: timedelta
    absolute: timedelta

    @classmethod
    def from_settings(cls, s: Settings) -> SessionPolicy:
        return cls(idle=timedelta(minutes=s.session_idle_minutes), absolute=timedelta(hours=s.session_absolute_hours))


def create_session(
    db: Session, user_id: uuid.UUID, role: str, policy: SessionPolicy, now: datetime
) -> tuple[str, AuthSession]:
    token = new_token()
    row = AuthSession(
        session_id=uuid.uuid4(),
        token_hash=token_hash(token),
        user_id=user_id,
        role_at_issue=role,
        created_at=now,
        last_seen_at=now,
        idle_expires_at=min(now + policy.idle, now + policy.absolute),
        absolute_expires_at=now + policy.absolute,
    )
    db.add(row)
    return token, row


def find_by_token(db: Session, token: str) -> AuthSession | None:
    return db.execute(select(AuthSession).where(AuthSession.token_hash == token_hash(token))).scalar_one_or_none()


def touch(row: AuthSession, policy: SessionPolicy, now: datetime) -> None:
    row.last_seen_at = now
    row.idle_expires_at = min(now + policy.idle, row.absolute_expires_at)


def revoke(row: AuthSession, reason: str, now: datetime) -> None:
    if row.revoked_at is None:
        row.revoked_at = now
        row.revocation_reason = reason


def revoke_all_for_user(db: Session, user_id: uuid.UUID, reason: str, now: datetime) -> int:
    result = db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now, revocation_reason=reason)
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]
