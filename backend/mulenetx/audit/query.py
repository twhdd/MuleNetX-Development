"""Audit event reads (SRS §19.2 `GET /audit`, §24.3). Newest first; the filters combine with AND."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mulenetx.core.pagination import PageRequest
from mulenetx.core.timeutil import isoformat_utc
from mulenetx.db.models.audit import AuditEvent

OUTCOMES = ("SUCCESS", "DENIED", "FAILED")


@dataclass(frozen=True)
class AuditFilter:
    user_id: uuid.UUID | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    outcome: str | None = None
    request_id: str | None = None
    start: datetime | None = None
    end: datetime | None = None


def event_view(e: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": str(e.event_id),
        "user_id": None if e.user_id is None else str(e.user_id),
        "action": e.action,
        "resource_type": e.resource_type,
        "resource_id": e.resource_id,
        "outcome": e.outcome,
        "timestamp": isoformat_utc(e.timestamp),
        "request_id": e.request_id,
        "metadata": e.metadata_ or {},
    }


def list_events(db: Session, f: AuditFilter, page: PageRequest) -> tuple[list[AuditEvent], int]:
    q = select(AuditEvent)
    for column, value in (
        (AuditEvent.user_id, f.user_id),
        (AuditEvent.action, f.action),
        (AuditEvent.resource_type, f.resource_type),
        (AuditEvent.resource_id, f.resource_id),
        (AuditEvent.outcome, f.outcome),
        (AuditEvent.request_id, f.request_id),
    ):
        if value is not None:
            q = q.where(column == value)
    if f.start is not None:
        q = q.where(AuditEvent.timestamp >= f.start)
    if f.end is not None:
        q = q.where(AuditEvent.timestamp <= f.end)
    total = int(db.execute(select(func.count()).select_from(q.subquery())).scalar_one())
    rows = db.execute(
        q.order_by(AuditEvent.timestamp.desc(), AuditEvent.event_id).offset(page.offset).limit(page.page_size)
    ).scalars()
    return list(rows), total
