"""Temporal features F27–F30 (SRS §15.3–§15.7)."""

import pytest

from mulenetx.features.encoding import State
from mulenetx.features.registry import load
from mulenetx.features.temporal import (
    build_out_index,
    cyclic_activity_score,
    dormancy_to_activity,
    rapid_in_out_ratio,
    short_lived_activity_score,
)
from tests.featutil import H, ev, sort

REG = load()


def test_rapid_in_out_greedy_matching() -> None:
    events = sort(
        [
            ev(0, 100, "in", "A", tx_id="i1"),
            ev(0.5, 90, "out", "B", tx_id="o1"),
            ev(1, 50, "in", "A", tx_id="i2"),
            ev(3, 40, "out", "B", tx_id="o2"),
            ev(5, 10, "in", "A", tx_id="i3"),
            ev(5 + 10 / 60, 9, "out", "B", tx_id="o3"),
            ev(5 + 20 / 60, 1, "out", "B", tx_id="o4"),
        ]
    )
    assert rapid_in_out_ratio(events, 6 * H, REG) == (pytest.approx(2 / 3), State.OBSERVED)


def test_rapid_window_and_zero() -> None:
    assert rapid_in_out_ratio([], 6 * H, REG) == (0.0, State.ZERO)
    old = sort([ev(0, 1, "in", "A"), ev(0.1, 1, "out", "B")])
    assert rapid_in_out_ratio(old, 30 * H, REG) == (0.0, State.ZERO)  # no inbound in the 24 h window


def test_dormancy_available_with_7_active_days() -> None:
    day = 24
    T = 40 * day * H
    prior = [ev(T / H - 24 - d * day - 1, 1, "in", "A") for d in range(7)] * 2
    recent = [ev(T / H - 1, 1, "in", "B"), ev(T / H - 2, 1, "in", "C"), ev(T / H - 3, 1, "in", "D")]
    v, s = dormancy_to_activity(sort(prior + recent), int(T), REG)
    assert s == State.OBSERVED and v == 3.0  # mean daily = 14 / 30 < 1


def test_short_lived_periods() -> None:
    times = [0, 10, 40, 100, 200]
    assert short_lived_activity_score(sort([ev(t, 1, "in", "A") for t in times]), 300 * H, REG) == (1.0, State.OBSERVED)
    long = [0, 20, 40, 60, 80, 150]
    assert short_lived_activity_score(sort([ev(t, 1, "in", "A") for t in long]), 160 * H, REG) == (0.0, State.OBSERVED)
    open_only = [0, 1]
    assert short_lived_activity_score(sort([ev(t, 1, "in", "A") for t in open_only]), 2 * H, REG) == (0.0, State.ZERO)


def test_cyclic_activity() -> None:
    rows = [
        (1 * H, "t1", "X", "A"),
        (2 * H, "t2", "A", "B"),
        (3 * H, "t3", "B", "X"),
        (5 * H, "t4", "X", "C"),
        (4 * H, "t5", "C", "X"),
    ]
    rows.sort()
    index = build_out_index(rows, 10 * H, REG.window("F29"))
    events = sort(
        [
            ev(1, 1, "out", "A", tx_id="t1"),
            ev(3, 1, "in", "B", tx_id="t3"),
            ev(5, 1, "out", "C", tx_id="t4"),
            ev(4, 1, "in", "C", tx_id="t5"),
        ]
    )
    v, s = cyclic_activity_score("X", events, index, 10 * H, REG, 1_000_000)
    assert s == State.OBSERVED and v == 0.5  # t1 and t3 are on the time-ordered cycle; t4/t5 are not ordered


def test_cycle_span_limit() -> None:
    rows = sorted([(1 * H, "t1", "X", "A"), (30 * H, "t2", "A", "X")])
    index = build_out_index(rows, 40 * H, REG.window("F29"))
    events = sort([ev(1, 1, "out", "A", tx_id="t1"), ev(30, 1, "in", "A", tx_id="t2")])
    assert cyclic_activity_score("X", events, index, 40 * H, REG, 1_000_000)[0] == 0.0
