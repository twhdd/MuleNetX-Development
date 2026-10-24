"""Graph metrics of SRS §8.3 on the NetworkX reference tier (DEC-01)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import networkx as nx

from mulenetx.analytics.projection import Projection
from mulenetx.core.decimal import D, round7


@dataclass(frozen=True)
class AlgorithmConfig:
    damping: float
    max_iterations: int
    tolerance: float

    def as_dict(self) -> dict[str, object]:
        return {
            "pagerank": {
                "projection": "directed weighted simple (TRANSFERRED_TO)",
                "weight": "total_amount per ordered pair",
                "damping": self.damping,
                "max_iterations": self.max_iterations,
                "tolerance": self.tolerance,
                "dangling": "uniform redistribution",
            },
            "betweenness": {
                "algorithm": "Brandes exact",
                "projection": "directed unweighted simple",
                "normalized": True,
            },
            "components": {
                "algorithm": "weakly connected components",
                "projection": "undirected simple",
                "component_id": "minimum account_id",
            },
            "degree": {
                "degree": "undirected unique neighbours",
                "in_degree": "unique incoming counterparties",
                "out_degree": "unique outgoing counterparties",
            },
        }


@dataclass(frozen=True)
class AccountMetrics:
    degree: int
    in_degree: int
    out_degree: int
    pagerank_raw: float
    pagerank_norm: Decimal
    betweenness_raw: float
    component_id: str
    component_size: int


def degrees(proj: Projection) -> dict[str, tuple[int, int, int]]:
    ins: dict[str, set[str]] = {n: set() for n in proj.nodes}
    outs: dict[str, set[str]] = {n: set() for n in proj.nodes}
    for p in proj.pairs:
        outs[p.source].add(p.destination)
        ins[p.destination].add(p.source)
    return {n: (len((ins[n] | outs[n]) - {n}), len(ins[n] - {n}), len(outs[n] - {n})) for n in proj.nodes}


def pagerank(proj: Projection, cfg: AlgorithmConfig) -> dict[str, float]:
    g = proj.directed_weighted()
    if g.number_of_nodes() == 0:
        return {}
    result: dict[str, float] = nx.pagerank(
        g, alpha=cfg.damping, max_iter=cfg.max_iterations, tol=cfg.tolerance, weight="weight", dangling=None
    )
    return result


def min_max(values: dict[str, float]) -> dict[str, Decimal]:
    """Snapshot min-max to [0,1]; a constant series maps to 0 (§8.3, §8.4)."""
    if not values:
        return {}
    lo, hi = min(values.values()), max(values.values())
    if hi == lo:
        return dict.fromkeys(values, Decimal("0.0000000"))
    span = D(hi) - D(lo)
    return {k: round7((D(v) - D(lo)) / span) for k, v in values.items()}


def betweenness(proj: Projection) -> dict[str, float]:
    g = proj.directed_unweighted()
    result: dict[str, float] = nx.betweenness_centrality(g, normalized=True, endpoints=False)
    return result


def components(proj: Projection) -> dict[str, tuple[str, int]]:
    """account_id -> (component_id = minimum account_id in the component, component_size)."""
    out: dict[str, tuple[str, int]] = {}
    for comp in nx.connected_components(proj.undirected()):
        members = sorted(comp)
        for m in members:
            out[m] = (members[0], len(members))
    return out


def compute_metrics(proj: Projection, cfg: AlgorithmConfig) -> dict[str, AccountMetrics]:
    deg = degrees(proj)
    pr = pagerank(proj, cfg)
    pr_norm = min_max(pr)
    bc = betweenness(proj)
    comp = components(proj)
    return {
        n: AccountMetrics(
            degree=deg[n][0],
            in_degree=deg[n][1],
            out_degree=deg[n][2],
            pagerank_raw=pr[n],
            pagerank_norm=pr_norm[n],
            betweenness_raw=bc[n],
            component_id=comp[n][0],
            component_size=comp[n][1],
        )
        for n in proj.nodes
    }
