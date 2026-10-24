"""Transactional features: one hand-computed case per feature, caps and zero denominators (SRS §10.1)."""

import math

import pytest

from mulenetx.features.encoding import State
from mulenetx.features.registry import load
from mulenetx.features.transactional import compute
from tests.featutil import H, ev, sort

REG = load()
T = 40 * H


def _case():
    return sort(
        [
            ev(10, 100.0, "in", "A", "TRANSFER"),
            ev(20, 50.0, "out", "B", "CASH_OUT"),
            ev(21, 30.0, "out", "B", "CASH_OUT"),
            ev(30, 20.0, "in", "C", "PAYMENT"),
        ]
    )


@pytest.mark.parametrize(
    ("fid", "value"),
    [
        ("F01", 4),
        ("F02", 2),
        ("F03", 2),
        ("F04", 120.0),
        ("F05", 80.0),
        ("F06", 50.0),
        ("F07", 40.0),
        ("F08", math.sqrt(3800 / 3)),
        ("F09", 1.5),
        ("F10", 1.5),
        ("F20", 0.5),
        ("F21", 3),
        ("F22", 4 / 7),
        ("F23", 10.0),
        ("F24", 24000.0),
        ("F25", 1 / 3),
        ("F26", 1.0),
        ("F35", 1.0),
        ("F38", 3),
        ("F39", 0.75),
        ("F40", 0.5),
        ("F41", 50.0),
        ("F42", 20.0),
    ],
)
def test_hand_computed(fid: str, value: float) -> None:
    v, s = compute(_case(), T, REG)[fid]
    assert v == pytest.approx(value, rel=1e-12, abs=1e-12)
    assert s == State.OBSERVED


def test_cold_start_all_zero_states() -> None:
    out = compute([], T, REG)
    assert len(out) == 23
    assert all(v == 0.0 and s == State.ZERO for v, s in out.values())


def test_f09_cap_and_zero_incoming() -> None:
    capped = compute([ev(1, 1e10, "in", "A")], T, REG)["F09"]
    assert capped == (1e6, State.OBSERVED)
    no_in = compute([ev(1, 5.0, "out", "A")], T, REG)["F09"]
    assert no_in == (0.0, State.ZERO)


def test_f23_cap_negative_and_zero() -> None:
    week = 7 * 24
    grow = compute(sort([ev(1, 1.0, "in", "A"), ev(week + 2, 100.0, "in", "A")]), (week + 3) * H, REG)["F23"]
    assert grow == (10.0, State.OBSERVED)  # (100 - 1) / 1 = 99 → capped at 10
    drop = compute([ev(1, 10.0, "in", "A")], (week + 3) * H, REG)["F23"]
    assert drop == (-1.0, State.OBSERVED)
    double = compute(sort([ev(1, 10.0, "in", "A"), ev(week + 2, 20.0, "in", "A")]), (week + 3) * H, REG)["F23"]
    assert double == (1.0, State.OBSERVED)


def test_f08_single_transaction_is_zero_state() -> None:
    v, s = compute([ev(1, 7.0, "in", "A")], T, REG)["F08"]
    assert (v, s) == (0.0, State.ZERO)


def test_window_is_half_open() -> None:
    # a transaction exactly 24 h before T is outside (T−24h, T]; one at T is inside
    out = compute(sort([ev(16, 1.0, "in", "A"), ev(40, 1.0, "in", "B")]), T, REG)
    assert out["F21"][0] == 1


def test_future_transactions_are_never_passed_in() -> None:
    # callers pass only events with timestamp ≤ T; the burst buckets also stop at T
    out = compute([ev(40, 1.0, "in", "A")], T, REG)
    assert out["F26"] == (1.0, State.OBSERVED)


def test_burst_against_168_bucket_baseline() -> None:
    events = sort([ev(39.5, 1.0, "in", f"A{i}") for i in range(10)] + [ev(1, 1.0, "in", "Z")])
    v, _ = compute(events, T, REG)["F26"]
    assert v == 10.0  # mean = 11/168 < 1 → denominator 1
    many = sort(
        [ev(h, 1.0, "in", f"B{h}") for h in range(40 - 167, 41)] + [ev(40.1, 1.0, "in", f"C{i}") for i in range(9)]
    )
    v2, _ = compute(many, int(40.5 * H), REG)["F26"]
    assert v2 == pytest.approx(10 / max(177 / 168, 1.0))
