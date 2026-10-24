"""Decimal rounding half-even at 7 dp (SRS §12.4)."""

from decimal import Decimal

from mulenetx.core.decimal import D, clamp, round6, round7


def test_round7_half_even() -> None:
    assert round7(Decimal("0.12345675")) == Decimal("0.1234568")
    assert round7(Decimal("0.12345665")) == Decimal("0.1234566")
    assert round7(Decimal("0.49999995")) == Decimal("0.5000000")


def test_D_uses_shortest_repr() -> None:
    assert D(0.1) == Decimal("0.1")
    assert D(1) == Decimal("1")
    assert D("0.25") == Decimal("0.25")


def test_clamp() -> None:
    assert clamp(Decimal("1.2")) == Decimal("1")
    assert clamp(Decimal("-0.1")) == Decimal("0")
    assert clamp(Decimal("0.3")) == Decimal("0.3")


def test_round6() -> None:
    assert round6(Decimal("1.0000005")) == Decimal("1.000000")
    assert round6(Decimal("1.0000015")) == Decimal("1.000002")
