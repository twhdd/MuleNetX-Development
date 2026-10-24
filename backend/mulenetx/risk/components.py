"""Component normalization and component scores (SRS §12.2, §12.3, §8.4)."""

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from mulenetx.core.decimal import ZERO, D, clamp, round7
from mulenetx.features.encoding import State


def percentile_against_table(value: float, table: list[float]) -> float:
    """Linear interpolation between bracketing quantiles of the 101-point table, clamped to [0,1]. A value equal
    to a run of identical quantiles takes the middle of that run (OQ-52)."""
    if not table:
        raise ValueError("empty reference table")
    last = len(table) - 1
    lo = bisect_left(table, value)
    hi = bisect_right(table, value) - 1
    if lo <= hi:
        p = (lo + hi) / 2 / last
    elif lo == 0:
        p = 0.0
    elif lo > last:
        p = 1.0
    else:
        a, b = table[lo - 1], table[lo]
        p = ((lo - 1) + (value - a) / (b - a)) / last
    return min(1.0, max(0.0, p))


def normalize(
    fid: str,
    value: float,
    method: str,
    reference: Mapping[str, Any],
    snapshot_percentiles: Mapping[str, float] | None,
) -> float | None:
    """One input normalized to [0,1]; None when it cannot be normalized (treated as unavailable)."""
    if method == "identity":
        return min(1.0, max(0.0, value))
    if method == "x_over_x_plus_median":
        m = reference.get("median_positive")
        if m is None:
            return 0.0  # no positive values in the training population → the input is 0 (§12.2)
        return value / (value + float(m)) if value + float(m) > 0 else 0.0
    if method == "log1p_percentile_reference":
        table = reference.get("quantiles_log1p") or []
        if not table:
            return None
        return percentile_against_table(math.log1p(max(value, 0.0)), [float(x) for x in table])
    if method == "percentile_within_snapshot":
        if snapshot_percentiles is None or fid not in snapshot_percentiles:
            return None
        return snapshot_percentiles[fid]
    raise ValueError(f"unknown normalization {method}")


@dataclass(frozen=True)
class ComponentResult:
    score: Decimal
    available: bool
    inputs: dict[str, float | None]


def component(
    feature_set: list[str],
    values: Mapping[str, float],
    states: Mapping[str, int],
    normalization: Mapping[str, str],
    reference: Mapping[str, Mapping[str, Any]],
    snapshot_percentiles: Mapping[str, float] | None = None,
) -> ComponentResult:
    """Mean of the normalized available inputs (equal weights); 0 and UNAVAILABLE when none is available."""
    normalized: dict[str, float | None] = {}
    for fid in feature_set:
        if states.get(fid) in (State.UNAVAILABLE, State.NOT_APPLICABLE) or math.isnan(values.get(fid, math.nan)):
            normalized[fid] = None
            continue
        normalized[fid] = normalize(
            fid, float(values[fid]), normalization[fid], reference.get(fid, {}), snapshot_percentiles
        )
    available = [D(v) for v in normalized.values() if v is not None]
    if not available:
        return ComponentResult(ZERO, False, normalized)
    return ComponentResult(round7(clamp(sum(available, ZERO) / Decimal(len(available)))), True, normalized)
