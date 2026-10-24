"""AT-TEMP-02: with fewer than 7 active days in the prior 30 days, dormancy_to_activity is UNAVAILABLE."""

import math

from mulenetx.features.encoding import State
from mulenetx.features.registry import load
from mulenetx.features.temporal import dormancy_to_activity
from tests.featutil import H, ev, sort

REG = load()


def test_AT_TEMP_02_dormancy_unavailable() -> None:
    day = 24
    T = 40 * day * H
    six_days = [ev(T / H - 24 - d * day - 1, 1, "in", "A") for d in range(6)] * 3
    v, s = dormancy_to_activity(sort(six_days + [ev(T / H - 1, 1, "in", "B")]), int(T), REG)
    assert s == State.UNAVAILABLE and math.isnan(v)


def test_AT_TEMP_02_cold_start_unavailable() -> None:
    v, s = dormancy_to_activity([], 100 * H, REG)
    assert s == State.UNAVAILABLE and math.isnan(v)


def test_AT_TEMP_02_recent_day_does_not_count_as_prior() -> None:
    day = 24
    T = 40 * day * H
    # six prior days plus activity only inside (T − 24 h, T]: still 6 prior active days
    events = [ev(T / H - 24 - d * day - 1, 1, "in", "A") for d in range(6)] + [ev(T / H - 5, 1, "in", "B")]
    assert dormancy_to_activity(sort(events), int(T), REG)[1] == State.UNAVAILABLE
