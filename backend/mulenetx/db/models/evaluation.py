"""Evaluation runs and metrics (SRS §6.3.9)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, String
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    evaluation_run_id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_id: Mapped[UUID]
    model_version: Mapped[str] = mapped_column(String(100))
    test_snapshot_id: Mapped[UUID]
    scoring_run_id: Mapped[UUID]
    analytics_version: Mapped[str] = mapped_column(String(100))
    risk_logic_version: Mapped[str] = mapped_column(String(100))
    reference_construction_version: Mapped[str] = mapped_column(String(50))
    configuration: Mapped[dict[str, Any]]
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]


class EvaluationMetric(Base):
    __tablename__ = "evaluation_metrics"

    evaluation_run_id: Mapped[UUID] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(20), primary_key=True)
    metric: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[float | None] = mapped_column(DOUBLE_PRECISION)
    sample_count: Mapped[int] = mapped_column(BigInteger)
    availability: Mapped[str] = mapped_column(String(20))
    details: Mapped[dict[str, Any] | None]
