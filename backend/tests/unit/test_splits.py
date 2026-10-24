"""Split boundaries and windows (SRS §11.4)."""

from datetime import UTC, datetime, timedelta

from mulenetx.ml.splits import compute_boundaries, percentile_timestamp

H = 3600
BASE = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp())


def test_nearest_rank_percentile() -> None:
    epochs = [BASE + i * H for i in range(10)]
    assert percentile_timestamp(epochs, 0.70) == BASE + 6 * H  # rank ceil(7.0) = 7 → index 6
    assert percentile_timestamp(epochs, 0.85) == BASE + 8 * H  # rank ceil(8.5) = 9 → index 8


def test_boundaries_and_windows() -> None:
    epochs = sorted([BASE + i * H for i in range(10)] + [BASE + 6 * H + 1800])
    b = compute_boundaries(epochs, 3600)
    assert b.t0 == datetime(2020, 1, 1, tzinfo=UTC)
    assert b.t_test == datetime(2020, 1, 1, 9, tzinfo=UTC)
    # 11 timestamps: rank ceil(7.7)=8 → 06:30 floored to 06:00; rank ceil(9.35)=10 → 08:00
    assert b.t_train == datetime(2020, 1, 1, 6, tzinfo=UTC)
    assert b.t_val == datetime(2020, 1, 1, 8, tzinfo=UTC)
    w = b.windows()
    assert w["train"] == (b.t0 - timedelta(hours=1), b.t_train)
    assert w["val"] == (b.t_train, b.t_val) and w["test"] == (b.t_val, b.t_test)
    assert set(b.window_table()) == {"train", "val", "test"}


def test_windows_partition_the_timeline() -> None:
    epochs = [BASE + i * 1800 for i in range(40)]
    b = compute_boundaries(epochs, 3600)
    w = b.windows()
    for e in epochs:
        ts = datetime.fromtimestamp(e, UTC)
        hits = [k for k, (lo, hi) in w.items() if lo < ts <= hi]
        assert len(hits) == 1, ts
