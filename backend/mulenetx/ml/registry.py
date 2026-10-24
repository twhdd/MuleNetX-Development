"""Model registry (SRS §11.9, §11.11; §7.6 rule 3)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from mulenetx.db.models.lineage import ModelVersion, RiskLogicVersion
from mulenetx.features.registry import FEATURE_REGIME, load
from mulenetx.ml.model import INTERFACE_VERSION
from mulenetx.ml.target import TARGET_DEFINITION_ID


def compatible_model(session: Session) -> ModelVersion | None:
    """Latest model with the current feature version, regime, target definition and interface version."""
    reg = load()
    rows = session.execute(
        select(ModelVersion)
        .where(ModelVersion.feature_version == reg.feature_version, ModelVersion.feature_regime == FEATURE_REGIME)
        .order_by(ModelVersion.created_at.desc(), ModelVersion.model_version.desc())
    ).scalars()
    for m in rows:
        if m.target_definition.get("target_definition_id") != TARGET_DEFINITION_ID:
            continue
        if INTERFACE_VERSION not in m.implementation_version:
            continue
        if risk_logic_for_model(session, m.model_version) is None:
            continue
        return m
    return None


def risk_logic_for_model(session: Session, model_version: str) -> RiskLogicVersion | None:
    """The risk logic version created from that model's training population (normalization reference)."""
    rows = session.execute(select(RiskLogicVersion).order_by(RiskLogicVersion.created_at.desc())).scalars()
    for r in rows:
        if r.normalization_reference.get("model_version") == model_version:
            return r
    return None
