"""Feature registry v1 (SRS §10.1, §10.5). `definition_hash` = SHA-256 of the registry file bytes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

REGISTRY_FILE = Path(__file__).with_name("registry_v1.json")
REGISTRY_REFERENCE = "backend/mulenetx/features/registry_v1.json"
FEATURE_REGIME = "RISK_FEATURES_UNAVAILABLE"
RISK_DERIVED = ("F19", "F31", "F33", "F36", "F37")


@dataclass(frozen=True)
class FeatureDef:
    id: str
    name: str
    definition: str
    window: str
    window_seconds: int | None
    unavailable_when: str
    cold_start: str
    description: str
    datatype: str
    unit: str
    direction: str
    cap: float | None
    leakage_risk: str
    group: str


@dataclass(frozen=True)
class Registry:
    feature_version: str
    definition_hash: str
    features: tuple[FeatureDef, ...]
    parameters: dict[str, Any]
    epsilon: float

    @property
    def ids(self) -> list[str]:
        return [f.id for f in self.features]

    def index(self, feature_id: str) -> int:
        return self.ids.index(feature_id)

    def get(self, feature_id: str) -> FeatureDef:
        return self.features[self.index(feature_id)]

    def cap(self, feature_id: str) -> float:
        cap = self.get(feature_id).cap
        if cap is None:
            raise KeyError(f"{feature_id} has no cap")
        return cap

    def window(self, feature_id: str) -> int:
        w = self.get(feature_id).window_seconds
        if w is None:
            raise KeyError(f"{feature_id} has no window")
        return w


@lru_cache(maxsize=1)
def load(path: Path = REGISTRY_FILE) -> Registry:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    features = tuple(FeatureDef(**{k: v for k, v in entry.items()}) for entry in data["features"])
    return Registry(
        feature_version=data["feature_version"],
        definition_hash=hashlib.sha256(raw).hexdigest(),
        features=features,
        parameters=dict(data["parameters"]),
        epsilon=float(data["conventions"]["epsilon"]),
    )
