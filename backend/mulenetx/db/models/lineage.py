"""Snapshots, runs, versions and the active context (SRS §6.3.3)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import CHAR, BigInteger, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class GraphSnapshot(Base):
    __tablename__ = "graph_snapshots"

    graph_snapshot_id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_id: Mapped[UUID]
    ingestion_run_id: Mapped[UUID]
    purpose: Mapped[str] = mapped_column(String(20))
    data_cutoff: Mapped[datetime]
    pipeline_version: Mapped[str] = mapped_column(String(100))
    graph_schema_version: Mapped[str] = mapped_column(String(50))
    source_record_count: Mapped[int] = mapped_column(BigInteger)
    node_count: Mapped[int | None] = mapped_column(BigInteger)
    edge_count: Mapped[int | None] = mapped_column(BigInteger)
    validation_digest: Mapped[str | None] = mapped_column(CHAR(64))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime]
    ready_at: Mapped[datetime | None]


class AnalyticsRun(Base):
    __tablename__ = "analytics_runs"

    analytics_run_id: Mapped[UUID] = mapped_column(primary_key=True)
    graph_snapshot_id: Mapped[UUID]
    analytics_version: Mapped[str] = mapped_column(String(100))
    engine: Mapped[str] = mapped_column(String(30))
    algorithm_configuration: Mapped[dict[str, Any]]
    started_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(String(20))
    error_summary: Mapped[str | None]


class FeatureVersion(Base):
    __tablename__ = "feature_versions"

    feature_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    definition_hash: Mapped[str] = mapped_column(CHAR(64))
    feature_count: Mapped[int]
    feature_registry_reference: Mapped[str]
    created_at: Mapped[datetime]


class ModelVersion(Base):
    __tablename__ = "model_versions"

    model_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    model_type: Mapped[str] = mapped_column(String(100))
    target_definition: Mapped[dict[str, Any]]
    feature_version: Mapped[str] = mapped_column(String(100))
    feature_regime: Mapped[str] = mapped_column(String(40))
    training_dataset_id: Mapped[UUID]
    training_snapshot_ids: Mapped[dict[str, Any]]
    split_boundaries: Mapped[dict[str, Any]]
    training_config: Mapped[dict[str, Any]]
    class_distribution: Mapped[dict[str, Any]]
    evaluation_metrics: Mapped[dict[str, Any]]
    operating_threshold: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    artifact_reference: Mapped[str]
    artifact_sha256: Mapped[str] = mapped_column(CHAR(64))
    implementation_version: Mapped[str] = mapped_column(String(100))
    random_seed: Mapped[int]
    created_at: Mapped[datetime]


class RiskLogicVersion(Base):
    __tablename__ = "risk_logic_versions"

    risk_logic_version: Mapped[str] = mapped_column(String(100), primary_key=True)
    formula_identifier: Mapped[str] = mapped_column(String(100))
    configuration: Mapped[dict[str, Any]]
    normalization_reference: Mapped[dict[str, Any]]
    rules: Mapped[dict[str, Any]]
    tier_thresholds: Mapped[dict[str, Any]]
    propagation_parameters: Mapped[dict[str, Any]]
    ring_parameters: Mapped[dict[str, Any]]
    created_at: Mapped[datetime]


class ScoringRun(Base):
    __tablename__ = "scoring_runs"

    scoring_run_id: Mapped[UUID] = mapped_column(primary_key=True)
    graph_snapshot_id: Mapped[UUID]
    analytics_run_id: Mapped[UUID]
    as_of: Mapped[datetime]
    feature_version: Mapped[str] = mapped_column(String(100))
    feature_snapshot_id: Mapped[UUID]
    model_version: Mapped[str | None] = mapped_column(String(100))
    risk_logic_version: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
    status: Mapped[str] = mapped_column(String(20))
    accounts_scored: Mapped[int | None] = mapped_column(BigInteger)


class ActiveContext(Base):
    __tablename__ = "active_context"

    singleton: Mapped[bool] = mapped_column(primary_key=True)
    dataset_id: Mapped[UUID | None]
    graph_snapshot_id: Mapped[UUID | None]
    analytics_run_id: Mapped[UUID | None]
    scoring_run_id: Mapped[UUID | None]
    model_version: Mapped[str | None] = mapped_column(String(100))
    risk_logic_version: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[datetime]
    updated_by_pipeline_run_id: Mapped[UUID | None]
