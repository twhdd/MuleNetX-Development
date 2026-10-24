"""AT-ML-01: positive / negative / unlabelled / excluded observations follow SRS §11.2; MERCHANT is excluded."""

from datetime import timedelta

import pytest

from mulenetx.api.deps import get_services
from mulenetx.ml.dataset_builder import population
from mulenetx.ml.target import label, label_from_counts
from tests.apiutil import _Req
from tests.seed import ANCHOR, seed_dataset

pytestmark = pytest.mark.integration


def test_AT_ML_01_label_rule() -> None:
    assert label([False, True]) == 1
    assert label([False, False]) == 0
    assert label([]) is None  # no transaction in W
    assert label([False, None]) is None  # a transaction without a label → UNLABELLED, never 0
    assert label([None, True]) == 1  # any positive is positive
    assert label_from_counts(3, 0, 3) == 0 and label_from_counts(3, 0, 2) is None and label_from_counts(0, 0, 0) is None


def test_AT_ML_01_population_classes(app) -> None:
    rt = get_services(_Req(app)).runtime
    edges = [
        ("CP", "CQ", 10.0, 1),  # 1: fraud → CP and CQ positive
        ("CN", "CR", 5.0, 2),  # 2: clean
        ("CU", "CR", 7.0, 2),  # 3: label NULL below → CU unlabelled, CR unlabelled
        ("CM", "M1", 3.0, 2),  # 4: merchant destination excluded
        ("CL", "CN", 1.0, 9),  # 5: outside the window
    ]
    ds = seed_dataset(rt, edges, key="tgt", fraud={1}, unlabelled={3})
    window = (ANCHOR, ANCHOR + timedelta(hours=5))
    members, excluded = population(rt, ds.dataset_id, window, assigned={"tgt:CQ"})
    labels = dict(members)
    assert labels["tgt:CP"] == 1
    assert labels["tgt:CN"] == 0
    assert labels["tgt:CU"] is None and labels["tgt:CR"] is None  # unlabelled stays None
    assert "tgt:M1" not in labels and excluded["merchant"] == 1
    assert "tgt:CQ" not in labels and excluded["earlier_split"] == 1  # assigned to an earlier split
    assert "tgt:CL" not in labels  # no transaction in W
    assert excluded["unlabelled"] == 2
