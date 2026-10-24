"""Replaceable model interface (SRS §11.1) and the XGBoost implementation (§11.8)."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from importlib.metadata import version as pkg_version
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import xgboost as xgb

from mulenetx.core.config import Settings

INTERFACE_VERSION = "model-interface-v1"
MODEL_TYPE = "xgboost-binary-classifier"


class FraudModel(Protocol):
    def train(self, x: np.ndarray, y: np.ndarray) -> None: ...
    def predict(self, x: np.ndarray) -> np.ndarray: ...
    def save(self, path: Path) -> None: ...
    def get_metadata(self) -> dict[str, Any]: ...


def hyperparameters(settings: Settings, scale_pos_weight: float) -> dict[str, Any]:
    s = settings
    return {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "n_estimators": s.xgb_n_estimators,
        "max_depth": s.xgb_max_depth,
        "learning_rate": s.xgb_learning_rate,
        "subsample": s.xgb_subsample,
        "colsample_bytree": s.xgb_colsample_bytree,
        "random_state": s.xgb_random_seed,
        "tree_method": "hist",
        "n_jobs": s.xgb_nthread,
        "missing": float("nan"),
        "scale_pos_weight": scale_pos_weight,
        "early_stopping": None,
    }


def implementation_version() -> str:
    return (
        f"python-{platform.python_version()}|xgboost-{xgb.__version__}|numpy-{pkg_version('numpy')}|"
        f"scikit-learn-{pkg_version('scikit-learn')}|{INTERFACE_VERSION}"
    )


def booster_params(params: dict[str, Any]) -> dict[str, Any]:
    """Map the §11.8 configuration to native XGBoost booster parameters."""
    return {
        "objective": params["objective"],
        "eval_metric": params["eval_metric"],
        "max_depth": params["max_depth"],
        "eta": params["learning_rate"],
        "subsample": params["subsample"],
        "colsample_bytree": params["colsample_bytree"],
        "seed": params["random_state"],
        "tree_method": params["tree_method"],
        "nthread": params["n_jobs"],
        "scale_pos_weight": params["scale_pos_weight"],
    }


@dataclass
class XGBoostModel:
    """Native-booster implementation (the scikit-learn wrapper is not used; OQ-48)."""

    params: dict[str, Any]
    booster: xgb.Booster | None = None

    def train(self, x: np.ndarray, y: np.ndarray) -> None:
        dtrain = xgb.DMatrix(x, label=y, missing=float("nan"))
        self.booster = xgb.train(booster_params(self.params), dtrain, num_boost_round=int(self.params["n_estimators"]))

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.booster is None:
            raise RuntimeError("model is not trained or loaded")
        result: np.ndarray = self.booster.predict(xgb.DMatrix(x, missing=float("nan")))
        return result

    def save(self, path: Path) -> None:
        if self.booster is None:
            raise RuntimeError("model is not trained")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.booster.save_model(str(path))

    @classmethod
    def load(cls, path: Path, params: dict[str, Any]) -> XGBoostModel:
        booster = xgb.Booster(model_file=str(path))
        booster.set_param({"nthread": int(params.get("n_jobs", 1))})
        return cls(params=params, booster=booster)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "model_type": MODEL_TYPE,
            "interface_version": INTERFACE_VERSION,
            "params": {k: (None if isinstance(v, float) and v != v else v) for k, v in self.params.items()},
        }
