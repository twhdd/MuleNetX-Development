"""AT-PROP-02: propagation on cyclic graphs terminates within the distance bound."""

from decimal import Decimal

from mulenetx.propagation.bfs import propagate, undirected_adjacency


def test_AT_PROP_02_cycle_terminates() -> None:
    ring = [(f"N{i}", f"N{(i + 1) % 12}") for i in range(12)]
    dense = [(f"K{i}", f"K{j}") for i in range(8) for j in range(8) if i != j]
    adj = undirected_adjacency(ring + dense + [("N0", "K0")])
    pre = {n: Decimal("0.9") for n in adj}
    out = propagate(adj, pre, Decimal("0.50"), 3, Decimal("0.50"), 5)
    assert all(c.distance <= 3 for items in out.values() for c in items)
    assert all(len(items) <= 5 for items in out.values())
    assert out["N6"][0].distance == 1  # every account is a source; neighbours win at d = 1
