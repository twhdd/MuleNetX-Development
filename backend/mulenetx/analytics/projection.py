"""Account projection export (SRS §8.1, §3.5): the snapshot's transactions from PostgreSQL, aggregated per
ordered pair, inserted into NetworkX graphs in canonical order (nodes by `account_id`, edges by
`(source, destination)`)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

import networkx as nx
from sqlalchemy import Engine, text


@dataclass(frozen=True)
class PairAggregate:
    source: str
    destination: str
    tx_count: int
    total_amount: Decimal


@dataclass
class Projection:
    nodes: list[str]
    pairs: list[PairAggregate]

    def directed_weighted(self) -> nx.DiGraph:
        g = nx.DiGraph()
        g.add_nodes_from(self.nodes)
        for p in self.pairs:
            if p.source != p.destination:
                g.add_edge(p.source, p.destination, weight=float(p.total_amount))
        return g

    def directed_unweighted(self) -> nx.DiGraph:
        g = nx.DiGraph()
        g.add_nodes_from(self.nodes)
        g.add_edges_from((p.source, p.destination) for p in self.pairs if p.source != p.destination)
        return g

    def undirected(self) -> nx.Graph:
        g = nx.Graph()
        g.add_nodes_from(self.nodes)
        g.add_edges_from((p.source, p.destination) for p in self.pairs if p.source != p.destination)
        return g

    def undirected_weighted(self) -> nx.Graph:
        """Weight = total_amount summed over both directions (Louvain, §8.3)."""
        weights: dict[tuple[str, str], Decimal] = {}
        for p in self.pairs:
            if p.source == p.destination:
                continue
            key = (p.source, p.destination) if p.source < p.destination else (p.destination, p.source)
            weights[key] = weights.get(key, Decimal(0)) + p.total_amount
        g = nx.Graph()
        g.add_nodes_from(self.nodes)
        for a, b in sorted(weights):
            g.add_edge(a, b, weight=float(weights[(a, b)]))
        return g


def export(engine: Engine, dataset_id: uuid.UUID, cutoff: datetime) -> Projection:
    p = {"d": dataset_id, "c": cutoff}
    with engine.connect() as conn:
        pairs = [
            PairAggregate(r.src, r.dst, int(r.n), r.total)
            for r in conn.execute(
                text(
                    """
                    SELECT source_account_id AS src, destination_account_id AS dst, count(*) AS n,
                           sum(amount) AS total
                    FROM transactions WHERE dataset_id = :d AND "timestamp" <= :c
                    GROUP BY source_account_id, destination_account_id
                    ORDER BY source_account_id, destination_account_id
                    """
                ),
                p,
            )
        ]
    nodes = sorted({x for pair in pairs for x in (pair.source, pair.destination)})
    return Projection(nodes=nodes, pairs=pairs)
