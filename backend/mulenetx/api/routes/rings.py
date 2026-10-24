"""Ring reads and review status (SRS §19.2 rings rows, §19.13, §9.4)."""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import (
    RingEvidenceOut,
    RingFeaturesOut,
    RingMemberPage,
    RingOut,
    RingPage,
    RingRiskOut,
    RingTransactionPage,
)
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import page_request
from mulenetx.core.timeutil import utcnow
from mulenetx.db.repositories import rings as repo
from mulenetx.db.repositories.context import active_lineage
from mulenetx.flow.analytic_paths import Budget

router = APIRouter(prefix="/api/v1/rings", tags=["rings"])


class StatusPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["CANDIDATE", "REVIEWED", "DISMISSED"]


def _score(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "min_score"}) from exc


def list_rings_body(
    services: Services,
    db: Session,
    candidate_class: str | None,
    status: str | None,
    min_score: str | None,
    scoring_run_id: uuid.UUID | None,
    page: int | None,
    page_size: int | None,
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    return repo.list_rings(db, req, s.pagination_count_cap, candidate_class, status, _score(min_score), scoring_run_id)


@router.get("", response_model=RingPage)
def list_rings(
    candidate_class: str | None = Query(default=None, alias="class"),
    status: str | None = Query(default=None),
    min_score: str | None = Query(default=None),
    scoring_run_id: uuid.UUID | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("ring.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    return list_rings_body(services, db, candidate_class, status, min_score, scoring_run_id, page, page_size)


@router.get("/{ring_id}", response_model=RingOut)
def get_ring(
    ring_id: uuid.UUID, _p: Principal = Depends(require("ring.read")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return repo.ring_view(db, repo.get_candidate(db, ring_id), active_lineage(db))


@router.patch("/{ring_id}/status", response_model=RingOut)
def patch_status(
    ring_id: uuid.UUID,
    body: StatusPatch,
    request: Request,
    principal: Principal = Depends(require("ring.review")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    c = db.get(repo.RingCandidate, ring_id, with_for_update=True)
    if c is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "ring"})
    if body.status not in repo.STATUS_TRANSITIONS.get(c.candidate_status, set()):
        raise AppError(
            ec.CONFLICT, "This status change is not allowed.", {"from": c.candidate_status, "to": body.status}
        )
    previous = c.candidate_status
    c.candidate_status = body.status
    c.status_changed_by = principal.user_id
    c.status_changed_at = utcnow()
    services.audit.record_in(
        db,
        "ring.status",
        "ring",
        "SUCCESS",
        user_id=principal.user_id,
        resource_id=str(ring_id),
        metadata={"from": previous, "to": body.status},
    )
    db.commit()
    return repo.ring_view(db, c, active_lineage(db))


@router.get("/{ring_id}/accounts", response_model=RingMemberPage)
def ring_accounts(
    ring_id: uuid.UUID,
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("ring.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    return repo.accounts(db, repo.get_candidate(db, ring_id), req, s.pagination_count_cap)


@router.get("/{ring_id}/transactions", response_model=RingTransactionPage)
def ring_transactions(
    ring_id: uuid.UUID,
    page_size: int | None = Query(default=None),
    cursor: str | None = Query(default=None),
    _p: Principal = Depends(require("ring.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(None, page_size, s.default_page_size, s.max_page_size)
    return repo.transactions(db, repo.get_candidate(db, ring_id), req.page_size, cursor)


@router.get("/{ring_id}/features", response_model=RingFeaturesOut)
def ring_features(
    ring_id: uuid.UUID, _p: Principal = Depends(require("ring.read")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return repo.features(db, repo.get_candidate(db, ring_id))


@router.get("/{ring_id}/risk", response_model=RingRiskOut)
def ring_risk(
    ring_id: uuid.UUID, _p: Principal = Depends(require("ring.read")), db: Session = Depends(get_db)
) -> dict[str, Any]:
    return repo.risk(db, repo.get_candidate(db, ring_id))


@router.get("/{ring_id}/evidence", response_model=RingEvidenceOut)
def ring_evidence(
    ring_id: uuid.UUID,
    section: str | None = Query(default=None),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("ring.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    budget = Budget(s.analytic_max_depth, s.analytic_max_paths, s.analytic_max_expansions)
    c = repo.get_candidate(db, ring_id)
    return repo.evidence(db, services.runtime.engine, budget, c, section, req, s.pagination_count_cap)
