"""Potential fraud-ring candidates and ring intelligence (SRS §6.3.5)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class RingCandidate(Base):
    __tablename__ = "potential_fraud_ring_candidates"

    candidate_id: Mapped[UUID] = mapped_column(primary_key=True)
    community_id: Mapped[str] = mapped_column(String(64))
    analytics_run_id: Mapped[UUID]
    graph_snapshot_id: Mapped[UUID]
    scoring_run_id: Mapped[UUID]
    candidate_score: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    candidate_class: Mapped[str] = mapped_column(String(40))
    signal_summary: Mapped[dict[str, Any]]
    candidate_status: Mapped[str] = mapped_column(String(20))
    status_changed_by: Mapped[UUID | None]
    status_changed_at: Mapped[datetime | None]
    analytics_version: Mapped[str] = mapped_column(String(100))
    risk_logic_version: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime]


class RingMembership(Base):
    __tablename__ = "ring_memberships"

    ring_id: Mapped[UUID] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(160), primary_key=True)


class RingFeatureSet(Base):
    __tablename__ = "ring_feature_sets"

    ring_feature_set_id: Mapped[UUID] = mapped_column(primary_key=True)
    ring_id: Mapped[UUID]
    analytics_run_id: Mapped[UUID]
    community_id: Mapped[str] = mapped_column(String(64))
    graph_snapshot_id: Mapped[UUID]
    scoring_run_id: Mapped[UUID]
    analytics_version: Mapped[str] = mapped_column(String(100))
    feature_version: Mapped[str] = mapped_column(String(100))
    ring_size: Mapped[int]
    transaction_count: Mapped[int]
    start_time: Mapped[datetime | None]
    end_time: Mapped[datetime | None]
    temporal_span_seconds: Mapped[int] = mapped_column(BigInteger)
    suspicious_transaction_density: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    risk_concentration: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    temporal_coordination: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    money_flow_concentration: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    centrality_signal: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    fan_in_signal: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    fan_out_signal: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    cycle_presence: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    suspicious_path_density: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    eligible_path_count: Mapped[int]
    qualifying_path_count: Mapped[int]
    paths_truncated: Mapped[bool]
    availability: Mapped[dict[str, Any]]
    computed_at: Mapped[datetime]


class RingRiskAssessment(Base):
    __tablename__ = "ring_risk_assessments"

    ring_risk_assessment_id: Mapped[UUID] = mapped_column(primary_key=True)
    ring_id: Mapped[UUID]
    feature_set_id: Mapped[UUID]
    scoring_run_id: Mapped[UUID]
    member_risk: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    transaction_risk: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    topology_signal: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    temporal_signal: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    money_flow_signal: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    ring_risk_score: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    risk_tier: Mapped[str] = mapped_column(String(20))
    availability: Mapped[dict[str, Any]]
    risk_logic_version: Mapped[str] = mapped_column(String(100))
    analytics_version: Mapped[str] = mapped_column(String(100))
    feature_version: Mapped[str] = mapped_column(String(100))
    generated_at: Mapped[datetime]
