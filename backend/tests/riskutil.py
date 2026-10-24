"""Helpers for risk tests."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from mulenetx.core.config import Settings
from mulenetx.risk.compose import Components, Weights
from mulenetx.risk.config import risk_logic_content
from tests.conftest import make_settings

CONTENT = risk_logic_content(make_settings())
WEIGHTS = Weights.from_config(CONTENT["configuration"]["weights"])
THRESHOLDS = CONTENT["tier_thresholds"]
RULES = CONTENT["rules"]["rules"]


def components(v: dict[str, Any]) -> Components:
    return Components(
        ml_score=None if v["ml"] is None else Decimal(v["ml"]),
        graph=Decimal(v["graph"]),
        graph_available=v.get("graph_available", True),
        behavioral=Decimal(v["behavioral"]),
        behavioral_available=v.get("behavioral_available", True),
        rules=Decimal(v["rules"]),
    )


def settings() -> Settings:
    return make_settings()
