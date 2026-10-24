"""Inference with artifact compatibility checks (SRS §11.11, §11.12)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mulenetx.db.models.lineage import ModelVersion
from mulenetx.features.registry import FEATURE_REGIME
from mulenetx.ml.artifacts import sha256_file
from mulenetx.ml.model import INTERFACE_VERSION, XGBoostModel
from mulenetx.ml.target import TARGET_DEFINITION_ID


class ModelIncompatibleError(Exception):
    """ml_score unavailable with reason MODEL_INCOMPATIBLE."""


class ModelUnavailableError(Exception):
    """ml_score unavailable: the artifact is missing or unreadable."""


@dataclass(frozen=True)
class ScoringRequest:
    feature_version: str
    feature_regime: str = FEATURE_REGIME
    target_definition_id: str = TARGET_DEFINITION_ID
    interface_version: str = INTERFACE_VERSION


def load_model(mv: ModelVersion, request: ScoringRequest) -> XGBoostModel:
    """Verify artifact SHA-256, feature version, regime, target definition and interface version."""
    path = Path(mv.artifact_reference)
    if not path.is_file():
        raise ModelUnavailableError("artifact missing")
    if sha256_file(path) != mv.artifact_sha256:
        raise ModelIncompatibleError("artifact checksum mismatch")
    if mv.feature_version != request.feature_version:
        raise ModelIncompatibleError("feature_version mismatch")
    if mv.feature_regime != request.feature_regime:
        raise ModelIncompatibleError("feature_regime mismatch")
    if mv.target_definition.get("target_definition_id") != request.target_definition_id:
        raise ModelIncompatibleError("target definition mismatch")
    if request.interface_version not in mv.implementation_version:
        raise ModelIncompatibleError("interface version mismatch")
    return XGBoostModel.load(path, dict(mv.training_config.get("hyperparameters", {})))


def predict(model: XGBoostModel, matrix: np.ndarray) -> np.ndarray:
    return model.predict(matrix)
