"""Each §11.6 leakage check detects a crafted violation (and passes on clean data)."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from mulenetx.features.encoding import State
from mulenetx.features.registry import load
from mulenetx.ml import leakage
from mulenetx.ml.dataset_builder import SplitData, TrainingData
from mulenetx.ml.splits import SplitBoundaries

REG = load()
T0 = datetime(2020, 1, 1, tzinfo=UTC)


def _split(name: str, cutoff: datetime, accounts: list[str]) -> SplitData:
    states = np.zeros((len(accounts), 42), dtype=np.int16)
    for fid in ("F19", "F31", "F33", "F36", "F37"):
        states[:, REG.index(fid)] = State.UNAVAILABLE
    return SplitData(
        name,
        cutoff,
        (cutoff - timedelta(hours=1), cutoff),
        __import__("uuid").uuid4(),
        cutoff,
        __import__("uuid").uuid4(),
        __import__("uuid").uuid4(),
        accounts=list(accounts),
        labels=[0] * len(accounts),
        features=np.zeros((len(accounts), 42)),
        states=states,
        feature_as_of=[cutoff] * len(accounts),
    )


def _data() -> TrainingData:
    b = SplitBoundaries(T0, T0 + timedelta(hours=2), T0 + timedelta(hours=3), T0 + timedelta(hours=4), 3600)
    splits = {
        "train": _split("train", b.t_train, ["a", "b"]),
        "val": _split("val", b.t_val, ["c"]),
        "test": _split("test", b.t_test, ["d"]),
    }
    return TrainingData(__import__("uuid").uuid4(), b, splits, "v1", REG.ids)


def test_clean_data_passes_all() -> None:
    results = leakage.all_checks(_data(), REG, {"a", "b"}, {"c"}, {"train": 0, "val": 0, "test": 0})
    assert all(r.passed for r in results) and len(results) == 7


def test_check_1_future_feature_time() -> None:
    d = _data()
    d.splits["train"].feature_as_of[0] = d.splits["train"].cutoff + timedelta(hours=1)
    assert not leakage.check_1_feature_event_time(d).passed


def test_check_2_snapshot_after_cutoff() -> None:
    d = _data()
    d.splits["val"].snapshot_cutoff = d.splits["val"].cutoff + timedelta(hours=1)
    assert not leakage.check_2_graph_snapshot_cutoff(d).passed


def test_check_3_account_in_two_splits() -> None:
    d = _data()
    d.splits["test"].accounts.append("a")
    assert not leakage.check_3_entity_separation(d).passed


def test_check_4_label_column_in_feature_code(tmp_path: Path) -> None:
    (tmp_path / "bad.py").write_text("x = row.fraud_label\n")
    assert not leakage.check_4_no_label_columns(REG, tmp_path).passed
    assert leakage.check_4_no_label_columns(REG).passed  # the real feature code is clean


def test_check_5_risk_feature_populated() -> None:
    d = _data()
    d.splits["train"].states[0, REG.index("F31")] = State.OBSERVED
    assert not leakage.check_5_regime(d, REG).passed


def test_check_6_test_rows_used() -> None:
    assert not leakage.check_6_test_not_used({"a", "d"}, set(), _data()).passed
    assert not leakage.check_6_test_not_used({"a"}, {"d"}, _data()).passed


def test_check_7_label_outside_window() -> None:
    assert not leakage.check_7_label_window(_data(), {"train": 1}).passed
