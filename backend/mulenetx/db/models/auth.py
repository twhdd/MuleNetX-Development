"""Identity and access (SRS §6.3.1)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CHAR, String
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(String(20))
    is_active: Mapped[bool]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    last_login_at: Mapped[datetime | None]


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    session_id: Mapped[UUID] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(CHAR(64))
    user_id: Mapped[UUID]
    role_at_issue: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime]
    last_seen_at: Mapped[datetime]
    idle_expires_at: Mapped[datetime]
    absolute_expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    revocation_reason: Mapped[str | None] = mapped_column(String(30))
