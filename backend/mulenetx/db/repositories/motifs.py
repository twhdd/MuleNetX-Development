"""Temporal motif read model (SRS §19.14): account queries match any participating account."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.lineage import lineage_envelope
from mulenetx.core.pagination import PageRequest, offset_page
from mulenetx.core.timeutil import isoformat_utc
from mulenetx.db.models.motifs import TemporalMotif
from mulenetx.db.repositories.communities import _lineage, resolve_analytics_run
from mulenetx.db.repositories.context import active_lineage
from mulenetx.motifs.common import MOTIF_TYPES

INTERPRETATION = (
    "A motif is an analytical pattern detected in transaction timing and structure. It is not a fraud, mule or "
    "criminality classification, and its confidence is a pattern-strength score, not a risk measure."
)


def motif_view(m: TemporalMotif) -> dict[str, Any]:
    evidence = m.evidence
    return {
        "motif_id": str(m.motif_id),
        "motif_type": m.motif_type,
        "anchor_account_id": m.anchor_account_id,
        "start_time": isoformat_utc(m.start_time),
        "end_time": isoformat_utc(m.end_time),
        "temporal_window_seconds": m.temporal_window_seconds,
        "participating_account_ids": m.participating_account_ids,
        "participating_transaction_ids": m.participating_transaction_ids,
        "transaction_count": m.transaction_count,
        "motif_confidence": float(m.motif_confidence),
        "confidence_components": evidence.get("components", {}),
        "order_ambiguous": m.order_ambiguous,
        "truncated": bool(evidence.get("truncated", False)),
        "evidence": evidence,
        "detector_version": evidence.get("detector_version"),
        "analytics_version": m.analytics_version,
    }


def list_for_accounts(
    db: Session,
    accounts: Iterable[str],
    analytics_run_id: uuid.UUID | None,
    motif_type: str | None,
    start: datetime | None,
    end: datetime | None,
    page: PageRequest,
    cap: int,
) -> dict[str, Any]:
    if motif_type is not None and motif_type not in MOTIF_TYPES:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "type"})
    if start is not None and end is not None and start > end:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "start"})
    run = resolve_analytics_run(db, analytics_run_id)
    ids = sorted(set(accounts))
    q = select(TemporalMotif).where(
        # identical inputs and versions give identical motifs; a rerun's rows are the first run's (OQ-75)
        TemporalMotif.graph_snapshot_id == run.graph_snapshot_id,
        TemporalMotif.analytics_version == run.analytics_version,
        # `@>` uses the jsonb_path_ops GIN index on participating_account_ids
        or_(*(TemporalMotif.participating_account_ids.contains([a]) for a in ids)),
    )
    if motif_type is not None:
        q = q.where(TemporalMotif.motif_type == motif_type)
    if start is not None:
        q = q.where(TemporalMotif.end_time >= start)
    if end is not None:
        q = q.where(TemporalMotif.start_time <= end)
    total = int(db.execute(select(func.count()).select_from(q.subquery())).scalar_one())
    rows = db.execute(
        q.order_by(TemporalMotif.start_time, TemporalMotif.motif_type, TemporalMotif.motif_id)
        .offset(page.offset)
        .limit(page.page_size)
    ).scalars()
    body = offset_page([motif_view(m) for m in rows], page, total, cap)
    return {
        **body,
        "interpretation": INTERPRETATION,
        **lineage_envelope(_lineage(run), active_lineage(db), run.completed_at),
    }
