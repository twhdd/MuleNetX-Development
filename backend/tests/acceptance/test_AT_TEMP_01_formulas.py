"""AT-TEMP-01: known timestamps give the exact temporal formula values (F21–F30)."""

import pytest

from mulenetx.features.encoding import State
from mulenetx.features.registry import load
from mulenetx.features.temporal import (
    build_out_index,
    cyclic_activity_score,
    rapid_in_out_ratio,
    short_lived_activity_score,
)
from mulenetx.features.transactional import compute
from tests.featutil import H, ev, sort

REG = load()
T = 100 * H
# account X; times in hours
EVENTS = sort(
    [
        ev(10, 10, "in", "A", tx_id="t01"),  # lifetime only
        ev(80, 10, "in", "A", tx_id="t02"),  # inside 24 h window (76 h, 100 h]
        ev(80.25, 9, "out", "B", tx_id="t03"),  # rapid follow of t02 (15 min)
        ev(90, 5, "in", "C", tx_id="t04"),  # not followed within 1 h
        ev(99, 4, "out", "D", tx_id="t05"),
        ev(99.5, 1, "out", "D", tx_id="t06"),
    ]
)


def test_AT_TEMP_01_velocity_and_short_intervals() -> None:
    out = compute(EVENTS, T, REG)
    assert out["F21"] == (5.0, State.OBSERVED)  # t02..t06 in (76 h, 100 h]
    assert out["F22"] == (pytest.approx(6 / 7), State.OBSERVED)
    # 7-day gaps (h): 70, 0.25, 9.75, 9, 0.5 → two ≤ 1 h
    assert out["F25"] == (pytest.approx(2 / 5), State.OBSERVED)
    # buckets: hour 80 holds t02 and t03 (2), every other hour ≤ 1; mean = 6/168 < 1
    assert out["F26"] == (2.0, State.OBSERVED)
    assert out["F23"] == (10.0, State.OBSERVED)  # no previous-week volume, current > 0


def test_AT_TEMP_01_rapid_in_out() -> None:
    # inbound in window: t02, t04; matched: t02 → t03 (t04 has no outbound in [90 h, 91 h])
    assert rapid_in_out_ratio(EVENTS, T, REG) == (0.5, State.OBSERVED)


def test_AT_TEMP_01_short_lived() -> None:
    # periods: [10,10] completed (gap 70); [80, 99.5] not completed (T − 99.5 h < 24 h) → 1 short / 1 completed
    assert short_lived_activity_score(EVENTS, T, REG) == (1.0, State.OBSERVED)


def test_AT_TEMP_01_cyclic() -> None:
    rows = sorted([(80 * H, "c1", "X", "P"), (81 * H, "c2", "P", "Q"), (82 * H, "c3", "Q", "X")])
    index = build_out_index(rows, T, REG.window("F29"))
    events = sort(
        [ev(80, 1, "out", "P", tx_id="c1"), ev(82, 1, "in", "Q", tx_id="c3"), ev(85, 1, "in", "Z", tx_id="c4")]
    )
    assert cyclic_activity_score("X", events, index, T, REG, 1_000_000) == (pytest.approx(2 / 3), State.OBSERVED)
