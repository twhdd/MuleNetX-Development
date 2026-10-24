"""Network intervention scenarios and candidates (SRS §6.3.7)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import CHAR, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class InterventionScenario(Base):
    __tablename__ = "intervention_scenarios"

    scenario_id: Mapped[UUID] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(10))
    target_ring_id: Mapped[UUID]
    baseline_graph_snapshot_id: Mapped[UUID]
    scoring_run_id: Mapped[UUID]
    intervention_type: Mapped[str | None] = mapped_column(String(40))
    target_ids: Mapped[list[Any] | None]
    baseline_suspicious_flow: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    baseline_suspicious_paths: Mapped[int | None]
    baseline_reachable_suspicious_pairs: Mapped[int | None]
    baseline_risk_mass: Mapped[Decimal | None] = mapped_column(Numeric(20, 7))
    baseline_paths_truncated: Mapped[bool | None]
    eligible_candidate_ids: Mapped[list[Any] | None]
    ranking_configuration: Mapped[dict[str, Any]]
    ranking_configuration_hash: Mapped[str] = mapped_column(CHAR(64))
    analytics_version: Mapped[str] = mapped_column(String(100))
    risk_logic_version: Mapped[str] = mapped_column(String(100))
    requested_by: Mapped[UUID]
    job_id: Mapped[UUID | None]
    status: Mapped[str] = mapped_column(String(20))
    error_summary: Mapped[str | None]
    created_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]


class InterventionCandidate(Base):
    __tablename__ = "intervention_candidates"

    candidate_id: Mapped[UUID] = mapped_column(primary_key=True)
    scenario_id: Mapped[UUID] = mapped_column(primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(40))
    target_ids: Mapped[list[Any]]
    residual_suspicious_flow: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    flow_disruption: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    flow_disruption_percentage: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    residual_suspicious_paths: Mapped[int]
    normalized_path_disruption: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    residual_reachable_suspicious_pairs: Mapped[int]
    normalized_connectivity_disruption: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    residual_risk_mass: Mapped[Decimal] = mapped_column(Numeric(20, 7))
    residual_network_risk: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    normalized_risk_reduction: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    intervention_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    normalized_intervention_cost: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    intervention_score: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    rank_position: Mapped[int]
    affected_account_ids: Mapped[list[Any]]
    affected_path_ids: Mapped[list[Any]]
    alternative_path_ids: Mapped[list[Any]]
    unavailable_metrics: Mapped[list[Any]]
    evidence: Mapped[dict[str, Any]]
    created_at: Mapped[datetime]
