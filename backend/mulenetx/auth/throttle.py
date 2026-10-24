"""Login throttling (SRS §22.1): per username and per client IP, `login_max_failures` failures within
`login_window_minutes` → 429. Counted from audit events (`auth.login`, outcome FAILED) [PLAN DEFAULT T06]."""

from __future__ import annotations

import ipaddress
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mulenetx.db.models.audit import AuditEvent

LOGIN_ACTION = "auth.login"


def failures_since(db: Session, since: datetime, *, username: str | None = None, client_ip: str | None = None) -> int:
    q = (
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.action == LOGIN_ACTION,
            AuditEvent.outcome == "FAILED",
            AuditEvent.timestamp > since,
        )
    )
    if username is not None:
        q = q.where(AuditEvent.metadata_["username"].astext == username)
    if client_ip is not None:
        q = q.where(AuditEvent.metadata_["client_ip"].astext == client_ip)
    return int(db.execute(q).scalar_one())


def is_throttled(
    db: Session, username: str, client_ip: str, now: datetime, max_failures: int, window_minutes: int
) -> bool:
    since = now - timedelta(minutes=window_minutes)
    if failures_since(db, since, username=username) >= max_failures:
        return True
    return failures_since(db, since, client_ip=client_ip) >= max_failures


def client_ip(peer: str | None, forwarded_for: str | None) -> str:
    """The direct peer, or the first X-Forwarded-For hop when the peer is a private-network proxy (OQ-16)."""
    host = peer or "unknown"
    if forwarded_for:
        try:
            if ipaddress.ip_address(host).is_private:
                return forwarded_for.split(",")[0].strip()
        except ValueError:
            pass
    return host
