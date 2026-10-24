"""Percentile rank within a population (SRS §8.4)."""

from mulenetx.core.percentile import percentile_rank


def test_single_value_is_zero() -> None:
    assert percentile_rank([5.0]) == [0.0]


def test_empty() -> None:
    assert percentile_rank([]) == []


def test_distinct_values() -> None:
    assert percentile_rank([3.0, 1.0, 2.0]) == [1.0, 0.0, 0.5]


def test_ties() -> None:
    # values 1,2,2,3 ; n-1 = 3
    # 1: 0 smaller -> 0; 2: 1 smaller + 0.5*1 other equal -> 1.5/3 = 0.5; 3: 3/3 = 1
    assert percentile_rank([1.0, 2.0, 2.0, 3.0]) == [0.0, 0.5, 0.5, 1.0]


def test_all_equal() -> None:
    assert percentile_rank([4.0, 4.0, 4.0]) == [0.5, 0.5, 0.5]
