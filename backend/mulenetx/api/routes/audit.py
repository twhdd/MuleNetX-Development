"""Audit log read API (SRS §19.2: audit.read, ADMIN only)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import AuditEventOut, PageOf
from mulenetx.audit.query import OUTCOMES, AuditFilter, event_view, list_events
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import offset_page, page_request
from mulenetx.core.timeutil import parse_utc

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


def _time(name: str, value: str | None):  # type: ignore[no-untyped-def]
    if value is None:
        return None
    try:
        return parse_utc(value)
    except ValueError as exc:
        raise AppError(ec.VALIDATION_ERROR, details={"field": name}) from exc


@router.get("", response_model=PageOf[AuditEventOut])
def list_audit(
    user_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None, max_length=100),
    resource_type: str | None = Query(default=None, max_length=100),
    resource_id: str | None = Query(default=None, max_length=200),
    outcome: str | None = Query(default=None),
    request_id: str | None = Query(default=None, max_length=100),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("audit.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    if outcome is not None and outcome not in OUTCOMES:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "outcome"})
    f = AuditFilter(
        user_id, action, resource_type, resource_id, outcome, request_id, _time("start", start), _time("end", end)
    )
    if f.start is not None and f.end is not None and f.start > f.end:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "start"})
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    events, total = list_events(db, f, req)
    return offset_page([event_view(e) for e in events], req, total, s.pagination_count_cap)
