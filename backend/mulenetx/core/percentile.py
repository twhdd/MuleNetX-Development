"""Percentile rank within a population (SRS §8.4, §9 preamble).

`rank(v) = (count strictly smaller + 0.5 × count of other equal values) / (n − 1)` for n > 1, and 0
for n = 1. Deterministic and order-independent.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Sequence


def percentile_rank(values: Sequence[float]) -> list[float]:
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [0.0]
    ordered = sorted(values)
    denominator = n - 1
    ranks: list[float] = []
    for v in values:
        smaller = bisect_left(ordered, v)
        equal = bisect_right(ordered, v) - smaller
        ranks.append((smaller + 0.5 * (equal - 1)) / denominator)
    return ranks
