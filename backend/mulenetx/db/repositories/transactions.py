"""Transaction read model (TransactionService, SRS §19.6): keyset pages on (timestamp DESC, transaction_id DESC)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, literal, or_, select, tuple_
from sqlalchemy.orm import Session

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError, limit_exceeded
from mulenetx.core.pagination import decode_cursor, encode_cursor
from mulenetx.core.timeutil import isoformat_utc
from mulenetx.db.models.canonical import Transaction

DIRECTIONS = ("in", "out", "any")


def transaction_view(t: Transaction, account_id: str | None = None) -> dict[str, Any]:
    view: dict[str, Any] = {
        "transaction_id": t.transaction_id,
        "source_transaction_ref": t.source_transaction_ref,
        "dataset_id": str(t.dataset_id),
        "source_account_id": t.source_account_id,
        "destination_account_id": t.destination_account_id,
        "amount": format(t.amount, "f"),
        "timestamp": isoformat_utc(t.timestamp),
        "transaction_type": t.transaction_type,
        "fraud_label": t.fraud_label,
    }
    if account_id is not None:
        view["direction"] = "out" if t.source_account_id == account_id else "in"
    return view


def resolve_range(
    db: Session, account_id: str, start: datetime | None, end: datetime | None, max_days: int
) -> tuple[datetime, datetime] | None:
    """Apply the §19.6 range rule; default to the most recent `max_days` of the account's activity."""
    window = timedelta(days=max_days)
    if start is not None and end is not None:
        if start > end:
            raise AppError(ec.VALIDATION_ERROR, "start must not be after end.", {"field": "start"})
        if end - start > window:
            raise limit_exceeded("range_days", max_days)
        return start, end
    if start is not None:
        return start, start + window
    if end is not None:
        return end - window, end
    latest = db.execute(
        select(func.max(Transaction.timestamp)).where(
            or_(Transaction.source_account_id == account_id, Transaction.destination_account_id == account_id)
        )
    ).scalar_one()
    if latest is None:
        return None
    return latest - window, latest


def page_for_account(
    db: Session,
    account_id: str,
    *,
    start: datetime | None,
    end: datetime | None,
    tx_type: str | None,
    direction: str,
    page_size: int,
    cursor: str | None,
    max_days: int,
) -> dict[str, Any]:
    if direction not in DIRECTIONS:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "direction"})
    window = resolve_range(db, account_id, start, end, max_days)
    if window is None:
        return {"items": [], "next_cursor": None, "range": None}
    lo, hi = window
    if direction == "out":
        who = Transaction.source_account_id == account_id
    elif direction == "in":
        who = Transaction.destination_account_id == account_id
    else:
        who = or_(Transaction.source_account_id == account_id, Transaction.destination_account_id == account_id)
    stmt = select(Transaction).where(who, Transaction.timestamp >= lo, Transaction.timestamp <= hi)
    if tx_type is not None:
        stmt = stmt.where(Transaction.transaction_type == tx_type)
    if cursor is not None:
        c_ts, c_id = decode_cursor(cursor)
        stmt = stmt.where(
            tuple_(Transaction.timestamp, Transaction.transaction_id) < tuple_(literal(c_ts), literal(c_id))
        )
    rows = list(
        db.execute(
            stmt.order_by(Transaction.timestamp.desc(), Transaction.transaction_id.desc()).limit(page_size + 1)
        ).scalars()
    )
    more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = encode_cursor(rows[-1].timestamp, rows[-1].transaction_id) if more and rows else None
    return {
        "items": [transaction_view(t, account_id) for t in rows],
        "next_cursor": next_cursor,
        "range": {"start": isoformat_utc(lo), "end": isoformat_utc(hi)},
    }
