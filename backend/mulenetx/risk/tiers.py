"""Risk tiers (SRS §12.6) on the rounded final score: LOW [0, .25) MEDIUM [.25, .50) HIGH [.50, .75)
CRITICAL [.75, 1]. Thresholds come from the risk logic version."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from mulenetx.core.decimal import D


def tier(score: Decimal, thresholds: Mapping[str, str]) -> str:
    if score >= D(thresholds["CRITICAL"]):
        return "CRITICAL"
    if score >= D(thresholds["HIGH"]):
        return "HIGH"
    if score >= D(thresholds["MEDIUM"]):
        return "MEDIUM"
    return "LOW"
