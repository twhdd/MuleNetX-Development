"""Ingestion runs, pipeline runs and jobs (SRS §6.3.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    ingestion_run_id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_id: Mapped[UUID]
    pipeline_version: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(String(20))
    records_seen: Mapped[int] = mapped_column(BigInteger)
    records_accepted: Mapped[int] = mapped_column(BigInteger)
    records_rejected: Mapped[int] = mapped_column(BigInteger)
    records_duplicate: Mapped[int] = mapped_column(BigInteger)
    rejection_summary: Mapped[dict[str, Any]]
    error_summary: Mapped[str | None]


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    pipeline_run_id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_id: Mapped[UUID]
    ingestion_run_id: Mapped[UUID | None]
    current_state: Mapped[str] = mapped_column(String(30))
    graph_snapshot_id: Mapped[UUID | None]
    analytics_run_id: Mapped[UUID | None]
    scoring_run_id: Mapped[UUID | None]
    model_version: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
    failure_stage: Mapped[str | None] = mapped_column(String(30))
    failure_category: Mapped[str | None] = mapped_column(String(50))
    safe_failure_message: Mapped[str | None]
    resumable_from: Mapped[str | None] = mapped_column(String(30))


class Job(Base):
    __tablename__ = "jobs"

    job_id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict[str, Any]]
    status: Mapped[str] = mapped_column(String(20))
    lock_key: Mapped[int | None] = mapped_column(BigInteger)
    attempts: Mapped[int]
    max_attempts: Mapped[int]
    lease_owner: Mapped[str | None] = mapped_column(String(100))
    lease_expires_at: Mapped[datetime | None]
    requested_by: Mapped[UUID | None]
    request_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime]
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    failure_category: Mapped[str | None] = mapped_column(String(40))
    error_summary: Mapped[str | None]
