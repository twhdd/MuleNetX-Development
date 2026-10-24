"""AT-INT-05 (and §27.10 check 9): the RANK pool is exactly the accounts and edges of the baseline paths, one
candidate per account, in the §16A.4.3 order; an oversized pool fails rather than being filtered."""

import pytest

from mulenetx.interventions.pool import PoolTooLargeError, rank_pool
from tests.interventionutil import baseline, counterexample, counterexample_baseline

FX = counterexample()


def test_AT_INT_05_pool_exact() -> None:
    pool = rank_pool(counterexample_baseline(), 5000)
    assert [[s.operation_type, list(s.targets)] for s in pool] == FX["pool_order"]
    accounts = [s.targets[0] for s in pool if s.operation_type != "EDGE_REMOVAL"]
    assert sorted(accounts) == sorted(set(accounts)) == ["A", "B", "C", "D"]  # one candidate per account
    assert not any(s.operation_type == "ACCOUNT_SET_REMOVAL" for s in pool)  # never generated in RANK


def test_AT_INT_05_accounts_outside_P_are_not_eligible() -> None:
    # E hangs off the ring but lies on no qualifying path
    b = baseline([("A", "B", "10"), ("B", "E", "5")], {"A": "0.9", "B": "0.8", "E": "0.1"}, ["A", "B", "E"])
    targets = {s.targets[0] for s in rank_pool(b, 5000)}
    assert "E" not in targets and "B>E" not in targets


def test_AT_INT_05_order_by_score_then_path_count_then_id() -> None:
    # S → X1/X2 → T: X1 and X2 have equal (unavailable = 0) scores and path counts → account_id order
    edges = [("S", "X2", "5"), ("S", "X1", "5"), ("X1", "T", "5"), ("X2", "T", "5")]
    b = baseline(edges, {"S": "0.9", "T": "0.9"}, ["S", "T"])
    inter = [s.targets[0] for s in rank_pool(b, 5000) if s.operation_type == "INTERMEDIARY_REMOVAL"]
    assert inter == ["X1", "X2"]


def test_AT_INT_05_pool_limit() -> None:
    with pytest.raises(PoolTooLargeError):
        rank_pool(counterexample_baseline(), 7)  # 8 candidates
