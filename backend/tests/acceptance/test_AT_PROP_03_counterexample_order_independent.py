"""AT-PROP-03: the propagation counterexample gives B = 0.4966667 (MEDIUM) under any evaluation order."""

import itertools
import random
from decimal import Decimal

from mulenetx.propagation.bfs import propagate, propagated_risk, undirected_adjacency
from mulenetx.risk.compose import final
from mulenetx.risk.tiers import tier
from tests.ingestutil import expected
from tests.riskutil import THRESHOLDS, WEIGHTS

FIX = expected("propagation_counterexample")


def _run(edges, pre_items):  # type: ignore[no-untyped-def]
    adj = undirected_adjacency(edges)
    pre = dict(pre_items)
    out = propagate(adj, pre, Decimal("0.50"), 3, Decimal("0.50"), 5)
    results = {}
    for account, score in pre.items():
        p = propagated_risk(out.get(account))
        f = final(score, p, WEIGHTS)
        results[account] = (format(p, "f"), format(f, "f"), tier(f, THRESHOLDS))
    return results


def test_AT_PROP_03_counterexample_order_independent() -> None:
    pre_items = [(k, Decimal(v)) for k, v in FIX["pre"].items()]
    edges = [tuple(e) for e in FIX["edges"]]
    want = {k: (v["propagated"], v["final"], v["tier"]) for k, v in FIX["expected"].items()}
    rng = random.Random(3)
    orders = list(itertools.permutations(pre_items))
    for order in orders:
        shuffled_edges = edges[:]
        rng.shuffle(shuffled_edges)
        reversed_edges = [(b, a) for a, b in shuffled_edges]
        assert _run(shuffled_edges, order) == want
        assert _run(reversed_edges, order) == want
    # the order-dependent alternative (using final scores of already-processed accounts) would make A a
    # source for B: 0.48 + 0.10 · 0.515/2 = 0.50575 → HIGH; the acyclic order keeps B MEDIUM.
    assert want["B"][2] == "MEDIUM"
