"""Accounts and transactions (SRS §19.2, §19.6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from mulenetx.api.deps import Services, get_db, get_services, require
from mulenetx.api.schemas.responses import (
    AccountOut,
    AssessmentOut,
    FeaturesOut,
    PageOf,
    PropagationOut,
    ShapOut,
    TemporalOut,
    TransactionPage,
)
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError, limit_exceeded
from mulenetx.core.pagination import offset_page, page_request
from mulenetx.core.timeutil import ensure_utc
from mulenetx.db.repositories import accounts as account_repo
from mulenetx.db.repositories import risk as risk_repo
from mulenetx.db.repositories import transactions as tx_repo

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


def _utc(value: datetime | None, field: str) -> datetime | None:
    if value is None:
        return None
    try:
        return ensure_utc(value)
    except ValueError as exc:
        raise AppError(ec.VALIDATION_ERROR, "Timestamps must include a UTC offset.", {"field": field}) from exc


@router.get("", response_model=PageOf[AccountOut])
def search_accounts(
    q: str | None = Query(default=None),
    risk_tier: str | None = Query(default=None),
    account_type: str | None = Query(default=None),
    sort: str = Query(default="risk_score"),
    order: str = Query(default="desc"),
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("account.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    items, total = account_repo.search(
        db, req, q=q, risk_tier=risk_tier, account_type=account_type, sort=sort, order=order
    )
    return offset_page(items, req, total, s.pagination_count_cap)


@router.get("/{account_id}", response_model=AccountOut)
def get_account(
    account_id: str,
    _p: Principal = Depends(require("account.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return account_repo.get(db, account_id)


@router.get("/{account_id}/transactions", response_model=TransactionPage)
def account_transactions(
    account_id: str,
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    type: str | None = Query(default=None),  # noqa: A002 - SRS parameter name
    direction: str = Query(default="any"),
    page_size: int | None = Query(default=None),
    cursor: str | None = Query(default=None),
    _p: Principal = Depends(require("transaction.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    size = s.default_page_size if page_size is None else page_size
    if size < 1:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "page_size"})
    if size > s.max_page_size:
        raise limit_exceeded("page_size", s.max_page_size)
    account_repo.require(db, account_id)
    return tx_repo.page_for_account(
        db,
        account_id,
        start=_utc(start, "start"),
        end=_utc(end, "end"),
        tx_type=type,
        direction=direction,
        page_size=size,
        cursor=cursor,
        max_days=s.max_transaction_range_days,
    )


@router.get("/{account_id}/risk", response_model=AssessmentOut)
def account_risk(
    account_id: str,
    scoring_run_id: uuid.UUID | None = Query(default=None),
    _p: Principal = Depends(require("risk.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    account_repo.require(db, account_id)
    return risk_repo.risk(db, account_id, scoring_run_id)


@router.get("/{account_id}/risk/history", response_model=PageOf[AssessmentOut])
def account_risk_history(
    account_id: str,
    page: int | None = Query(default=None),
    page_size: int | None = Query(default=None),
    _p: Principal = Depends(require("risk.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    s = services.runtime.settings
    req = page_request(page, page_size, s.default_page_size, s.max_page_size)
    account_repo.require(db, account_id)
    items, total = risk_repo.history(db, account_id, req)
    return offset_page(items, req, total, s.pagination_count_cap)


@router.get("/{account_id}/risk/propagation", response_model=PropagationOut)
def account_risk_propagation(
    account_id: str,
    scoring_run_id: uuid.UUID | None = Query(default=None),
    _p: Principal = Depends(require("risk.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    account_repo.require(db, account_id)
    return risk_repo.propagation(db, account_id, scoring_run_id)


@router.get("/{account_id}/features", response_model=FeaturesOut)
def account_features(
    account_id: str,
    scoring_run_id: uuid.UUID | None = Query(default=None),
    _p: Principal = Depends(require("risk.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    account_repo.require(db, account_id)
    return risk_repo.features(db, account_id, scoring_run_id)


@router.get("/{account_id}/temporal", response_model=TemporalOut)
def account_temporal(
    account_id: str,
    scoring_run_id: uuid.UUID | None = Query(default=None),
    _p: Principal = Depends(require("temporal.read")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    account_repo.require(db, account_id)
    return risk_repo.temporal(db, account_id, scoring_run_id)


@router.get("/{account_id}/shap", response_model=ShapOut)
def account_shap(
    account_id: str,
    assessment_id: uuid.UUID | None = Query(default=None),
    top_n: int | None = Query(default=None),
    _p: Principal = Depends(require("shap.read")),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> dict[str, Any]:
    from mulenetx.explain.shap_service import explain

    s = services.runtime.settings
    n = s.shap_default_top_n if top_n is None else top_n
    if n < 1:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "top_n"})
    if n > s.shap_max_top_n:
        raise limit_exceeded("top_n", s.shap_max_top_n)
    account_repo.require(db, account_id)
    return explain(db, account_id, assessment_id, n)
