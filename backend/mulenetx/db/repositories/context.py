"""Active-context lookups shared by read services (SRS §6.9, §19.12)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from mulenetx.core.lineage import Lineage
from mulenetx.db.models.lineage import ActiveContext


def active(db: Session) -> ActiveContext:
    return db.execute(select(ActiveContext)).scalar_one()


def active_lineage(db: Session) -> Lineage:
    ctx = active(db)
    return Lineage(
        graph_snapshot_id=None if ctx.graph_snapshot_id is None else str(ctx.graph_snapshot_id),
        analytics_run_id=None if ctx.analytics_run_id is None else str(ctx.analytics_run_id),
        scoring_run_id=None if ctx.scoring_run_id is None else str(ctx.scoring_run_id),
        model_version=ctx.model_version,
        risk_logic_version=ctx.risk_logic_version,
    )
