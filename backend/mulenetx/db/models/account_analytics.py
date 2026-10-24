"""Account-level analytical results (SRS §6.3.4)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Float, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class AccountGraphMetrics(Base):
    __tablename__ = "account_graph_metrics"

    analytics_run_id: Mapped[UUID] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    degree: Mapped[int]
    in_degree: Mapped[int]
    out_degree: Mapped[int]
    pagerank_raw: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    pagerank_norm: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    betweenness_raw: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    component_id: Mapped[str] = mapped_column(String(64))
    component_size: Mapped[int]
    community_id: Mapped[str] = mapped_column(String(64))
    community_size: Mapped[int]


class AccountFeatureValues(Base):
    __tablename__ = "account_feature_values"

    feature_snapshot_id: Mapped[UUID] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    as_of: Mapped[datetime]
    feature_version: Mapped[str] = mapped_column(String(100))
    graph_snapshot_id: Mapped[UUID]
    analytics_run_id: Mapped[UUID]
    feature_values: Mapped[list[float]] = mapped_column(ARRAY(Float(precision=53)))
    feature_states: Mapped[list[int]] = mapped_column(ARRAY(SmallInteger))
    created_at: Mapped[datetime]


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    assessment_id: Mapped[UUID] = mapped_column(primary_key=True)
    scoring_run_id: Mapped[UUID]
    account_id: Mapped[str] = mapped_column(String(160))
    as_of: Mapped[datetime]
    graph_snapshot_id: Mapped[UUID]
    feature_snapshot_id: Mapped[UUID]
    model_version: Mapped[str | None] = mapped_column(String(100))
    feature_version: Mapped[str] = mapped_column(String(100))
    analytics_version: Mapped[str] = mapped_column(String(100))
    risk_logic_version: Mapped[str] = mapped_column(String(100))
    ml_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 7))
    graph_signal_score: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    behavioral_signal_score: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    rule_signal_score: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    pre_propagation_score: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    propagated_risk: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    final_score: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    risk_tier: Mapped[str] = mapped_column(String(20))
    signal_availability: Mapped[dict[str, Any]]
    fired_rules: Mapped[list[Any]]
    generated_at: Mapped[datetime]


class PropagationContribution(Base):
    __tablename__ = "propagation_contributions"

    scoring_run_id: Mapped[UUID] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    source_account_id: Mapped[str] = mapped_column(String(160))
    source_assessment_id: Mapped[UUID]
    distance: Mapped[int] = mapped_column(SmallInteger)
    source_score: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    decay_value: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    contribution: Mapped[Decimal] = mapped_column(Numeric(8, 7))
    rank: Mapped[int] = mapped_column(SmallInteger, primary_key=True)


class ShapExplanation(Base):
    __tablename__ = "shap_explanations"

    assessment_id: Mapped[UUID] = mapped_column(primary_key=True)
    model_version: Mapped[str] = mapped_column(String(100))
    feature_version: Mapped[str] = mapped_column(String(100))
    explainer: Mapped[str] = mapped_column(String(50))
    base_value: Mapped[float] = mapped_column(DOUBLE_PRECISION)
    output_space: Mapped[str] = mapped_column(String(20))
    contributions: Mapped[list[Any]]
    computed_at: Mapped[datetime]
