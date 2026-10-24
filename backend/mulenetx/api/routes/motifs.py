"""Temporal motif reads (SRS §19.2: motif.read; §19.14)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import MotifPage
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import page_request
from mulenetx.core.timeutil import parse_utc
from mulenetx.db.repositories import accounts as account_repo
from mulenetx.db.repositories import motifs as repo
from mulenetx.db.repositories import rings as ring_repo
from mulenetx.motifs.common import MOTIF_TYPES

router = APIRouter(prefix="/api/v1", tags=["motifs"])


def _time(name: str, value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return parse_utc(value)
    except ValueError as exc:
        raise AppError(ec.VALIDATION_ERROR, details={"field": name}) from exc


@router.get("/accounts/{account_id}/motifs", response_model=MotifPage)
def account_motifs(
    account_id: str,
    type: str | None = Query(default=None),  # noqa: A002 - SRS §19.2 parameter name
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    analytics_run_id: uuid.UUID | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("motif.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    since, until = _time("start", start), _time("end", end)
    if type is not None and type not in MOTIF_TYPES:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "type"})
    if since is not None and until is not None and since > until:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "start"})
    account_repo.require(db, account_id)
    return repo.list_for_accounts(db, [account_id], analytics_run_id, type, since, until, req, s.pagination_count_cap)


@router.get("/rings/{ring_id}/motifs", response_model=MotifPage)
def ring_motifs(
    ring_id: uuid.UUID,
    type: str | None = Query(default=None),  # noqa: A002 - SRS §19.2 parameter name
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("motif.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    """Motifs touching any ring member, in the ring's analytics context."""
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    since, until = _time("start", start), _time("end", end)
    if type is not None and type not in MOTIF_TYPES:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "type"})
    if since is not None and until is not None and since > until:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "start"})
    c = ring_repo.get_candidate(db, ring_id)
    members = ring_repo.member_ids(db, c)
    return repo.list_for_accounts(db, members, c.analytics_run_id, type, since, until, req, s.pagination_count_cap)
