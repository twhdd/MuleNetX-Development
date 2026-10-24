"""Temporal motifs (SRS §6.3.6)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class TemporalMotif(Base):
    __tablename__ = "temporal_motifs"

    motif_id: Mapped[UUID] = mapped_column(primary_key=True)
    analytics_run_id: Mapped[UUID]
    graph_snapshot_id: Mapped[UUID]
    motif_type: Mapped[str] = mapped_column(String(40))
    anchor_account_id: Mapped[str] = mapped_column(String(160))
    start_time: Mapped[datetime]
    end_time: Mapped[datetime]
    temporal_window_seconds: Mapped[int]
    participating_account_ids: Mapped[list[Any]]
    participating_transaction_ids: Mapped[list[Any]]
    transaction_count: Mapped[int]
    motif_confidence: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    order_ambiguous: Mapped[bool]
    evidence: Mapped[dict[str, Any]]
    analytics_version: Mapped[str] = mapped_column(String(100))
    computed_at: Mapped[datetime]
