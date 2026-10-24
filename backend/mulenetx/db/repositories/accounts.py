"""Account read model (AccountService, SRS §19.6). The projection columns are written only by activation."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.lineage import Lineage, is_stale
from mulenetx.core.pagination import PageRequest
from mulenetx.db.models.canonical import Account
from mulenetx.db.models.datasets import Dataset
from mulenetx.db.repositories.context import active, active_lineage

SORTS = {
    "account_id": Account.account_id,
    "source_account_ref": Account.source_account_ref,
    "risk_score": Account.risk_score,
    "risk_tier": Account.risk_tier,
}
TIERS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def _f(value: Any) -> float | None:
    return None if value is None else float(value)


def account_view(
    a: Account, dataset_key: str | None, active_dataset: uuid.UUID | None, lineage: Lineage
) -> dict[str, Any]:
    in_active = active_dataset is not None and a.dataset_id == active_dataset
    return {
        "account_id": a.account_id,
        "source_account_ref": a.source_account_ref,
        "dataset_id": str(a.dataset_id),
        "dataset_key": dataset_key,
        "account_type": a.account_type,
        "created_at": None if a.created_at is None else a.created_at.isoformat(),
        "risk_score": _f(a.risk_score),
        "risk_tier": a.risk_tier,
        "community_id": a.community_id,
        "latest_risk_assessment_id": None if a.latest_risk_assessment_id is None else str(a.latest_risk_assessment_id),
        "lineage": lineage.as_dict() if in_active else Lineage().as_dict(),
        "computed_at": None,
        "is_stale": not in_active or is_stale(lineage, lineage),
    }


def get(db: Session, account_id: str) -> dict[str, Any]:
    a = db.get(Account, account_id)
    if a is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "account"})
    ctx = active(db)
    key = db.execute(select(Dataset.dataset_key).where(Dataset.dataset_id == a.dataset_id)).scalar_one()
    return account_view(a, key, ctx.dataset_id, active_lineage(db))


def require(db: Session, account_id: str) -> Account:
    a = db.get(Account, account_id)
    if a is None:
        raise AppError(ec.NOT_FOUND, details={"resource": "account"})
    return a


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search(
    db: Session,
    page: PageRequest,
    *,
    q: str | None,
    risk_tier: str | None,
    account_type: str | None,
    sort: str,
    order: str,
) -> tuple[list[dict[str, Any]], int]:
    """Search within the active dataset (DEC-04): `q` is an exact or prefix match on `source_account_ref`."""
    if sort not in SORTS:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "sort"})
    if order not in ("asc", "desc"):
        raise AppError(ec.VALIDATION_ERROR, details={"field": "order"})
    if risk_tier is not None and risk_tier not in TIERS:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "risk_tier"})
    if q is not None and len(q) > 128:
        raise AppError(ec.LIMIT_EXCEEDED, details={"field": "q", "limit": 128})
    ctx = active(db)
    if ctx.dataset_id is None:
        return [], 0
    stmt: Select[tuple[Account]] = select(Account).where(Account.dataset_id == ctx.dataset_id)
    if q:
        stmt = stmt.where(Account.source_account_ref.like(_escape_like(q) + "%", escape="\\"))
    if risk_tier is not None:
        stmt = stmt.where(Account.risk_tier == risk_tier)
    if account_type is not None:
        stmt = stmt.where(Account.account_type == account_type)
    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one())
    column = SORTS[sort]
    ordered = column.desc().nulls_last() if order == "desc" else column.asc().nulls_last()
    rows = db.execute(stmt.order_by(ordered, Account.account_id).offset(page.offset).limit(page.page_size)).scalars()
    key = db.execute(select(Dataset.dataset_key).where(Dataset.dataset_id == ctx.dataset_id)).scalar_one()
    lineage = active_lineage(db)
    return [account_view(a, key, ctx.dataset_id, lineage) for a in rows], total
