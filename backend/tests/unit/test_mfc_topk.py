"""MFC (§9A.2): top-k = 3 paths by path flow, ties by the §16.5 order; 1 when ≤ 3 qualifying paths."""

from decimal import Decimal

from mulenetx.flow.analytic_paths import Budget
from mulenetx.rings.features import compute
from mulenetx.rings.inputs import ContextInputs
from mulenetx.rings.membership import membership
from tests.flowutil import context, projection_from_edges


def _ctx(edges, scores):  # type: ignore[no-untyped-def]
    return ContextInputs(context(scores), projection_from_edges(edges), {}, {}, [], Budget())


def test_at_most_three_paths_give_one() -> None:
    ctx = _ctx([("A", "B", "10"), ("B", "C", "20")], {"A": "0.9", "B": "0.9", "C": "0.9"})
    f = compute(ctx, membership(ctx, ["A", "B", "C"]))
    assert len(f.scope.qualifying_paths) == 3 and f.values["MFC"] == Decimal("1.0000000")


def test_flow_spread_over_many_paths() -> None:
    # S → Ti for six suspicious Ti with amounts 60, 50, 40, 30, 20, 10: top 3 carry 150 of 210
    edges = [("S", f"T{i}", str(60 - 10 * i)) for i in range(6)]
    scores = {"S": "0.9", **{f"T{i}": "0.9" for i in range(6)}}
    ctx = _ctx(edges, scores)
    f = compute(ctx, membership(ctx, ["S"]))
    assert len(f.scope.qualifying_paths) == 6
    assert f.values["MFC"] == Decimal("0.7142857")  # 150 / 210


def test_ties_break_by_path_order() -> None:
    # equal flows: the shorter / lexicographically first paths win the top-3 places deterministically
    edges = [("S", x, "10") for x in ("D", "C", "B", "A")]
    scores = {"S": "0.9", "A": "0.9", "B": "0.9", "C": "0.9", "D": "0.9"}
    ctx = _ctx(edges, scores)
    f = compute(ctx, membership(ctx, ["S"]))
    assert f.values["MFC"] == Decimal("0.7500000")  # any 3 of 4 equal flows: 30 / 40
