"""Graph metrics on the abc_chain fixture (SRS §8.3, §27.4); values hand-computed in expected.json."""

from decimal import Decimal

import pytest

from mulenetx.analytics.algorithms import AlgorithmConfig, compute_metrics, min_max
from mulenetx.analytics.communities import louvain
from mulenetx.analytics.projection import PairAggregate, Projection
from tests.ingestutil import expected

CFG = AlgorithmConfig(0.85, 100, 1e-6)


def _abc() -> Projection:
    return Projection(
        nodes=["CA", "CB", "CC"],
        pairs=[PairAggregate("CA", "CB", 1, Decimal("100")), PairAggregate("CB", "CC", 1, Decimal("50"))],
    )


def test_abc_metrics() -> None:
    exp = expected("abc_chain")["analytics"]
    metrics = compute_metrics(_abc(), CFG)
    for acc, m in metrics.items():
        assert [m.degree, m.in_degree, m.out_degree] == exp["degree"][acc]
        assert m.pagerank_raw == pytest.approx(exp["pagerank"][acc], abs=1e-6)
        assert float(m.pagerank_norm) == pytest.approx(exp["pagerank_norm"][acc], abs=1e-5)
        assert m.betweenness_raw == exp["betweenness"][acc]
        assert (m.component_id, m.component_size) == (exp["component"]["id"], exp["component"]["size"])
    assert sum(m.pagerank_raw for m in metrics.values()) == pytest.approx(1.0, abs=1e-9)


def test_abc_louvain_single_community() -> None:
    assert louvain(_abc(), 1.0, 42) == expected("abc_chain")["analytics"]["communities"]


def test_min_max_constant_series_is_zero() -> None:
    assert min_max({"a": 0.2, "b": 0.2}) == {"a": Decimal("0.0000000"), "b": Decimal("0.0000000")}
    assert min_max({}) == {}


def test_parallel_and_self_pairs_do_not_inflate_degree() -> None:
    proj = Projection(
        nodes=["A", "B"],
        pairs=[PairAggregate("A", "A", 2, Decimal("5")), PairAggregate("A", "B", 3, Decimal("7"))],
    )
    m = compute_metrics(proj, CFG)
    assert (m["A"].degree, m["A"].out_degree, m["A"].in_degree) == (1, 1, 0)
