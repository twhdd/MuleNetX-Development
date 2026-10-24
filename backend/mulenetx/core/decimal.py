"""Decimal score arithmetic (SRS §12.4).

Every stored NUMERIC(8,7) score passes through `round7` immediately before persistence and before
tier assignment. Floats (for example ML probabilities) enter the decimal domain through `D()`.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

SEVEN_DP = Decimal("0.0000001")
SIX_DP = Decimal("0.000001")
FOUR_DP = Decimal("0.0001")
ZERO = Decimal("0")
ONE = Decimal("1")


def D(value: Decimal | float | int | str) -> Decimal:  # noqa: N802 - name fixed by the plan (§3.3)
    """Convert to Decimal via `str()` so that a float's shortest repr is used, not its binary expansion."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round7(value: Decimal) -> Decimal:
    return value.quantize(SEVEN_DP, rounding=ROUND_HALF_EVEN)


def round6(value: Decimal) -> Decimal:
    return value.quantize(SIX_DP, rounding=ROUND_HALF_EVEN)


def round4(value: Decimal) -> Decimal:
    return value.quantize(FOUR_DP, rounding=ROUND_HALF_EVEN)


def clamp(value: Decimal, low: Decimal = ZERO, high: Decimal = ONE) -> Decimal:
    if value < low:
        return low
    if value > high:
        return high
    return value
