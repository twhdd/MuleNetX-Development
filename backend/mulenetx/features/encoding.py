"""Feature value states and model encoding (SRS §10.3)."""

from __future__ import annotations

import math
from enum import IntEnum


class State(IntEnum):
    OBSERVED = 0
    ZERO = 1
    UNAVAILABLE = 2
    NOT_APPLICABLE = 3


Value = tuple[float, State]

UNAVAILABLE: Value = (math.nan, State.UNAVAILABLE)


def observed(value: float, activity: bool = True) -> Value:
    """OBSERVED, or ZERO when the value is 0 because there was no qualifying activity."""
    if value == 0 and not activity:
        return (0.0, State.ZERO)
    return (float(value), State.OBSERVED)


def zero() -> Value:
    return (0.0, State.ZERO)


def encode(values: list[Value]) -> tuple[list[float], list[int]]:
    """Model vector: UNAVAILABLE and NOT_APPLICABLE become NaN; OBSERVED/ZERO keep their numeric value."""
    floats = [math.nan if s in (State.UNAVAILABLE, State.NOT_APPLICABLE) else v for v, s in values]
    return floats, [int(s) for _, s in values]
