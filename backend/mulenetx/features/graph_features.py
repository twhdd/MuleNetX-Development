"""Graph features F11–F18 from the snapshot used (SRS §10.1, §10.4) and the risk-derived features that are
UNAVAILABLE under regime RISK_FEATURES_UNAVAILABLE (F19, F31, F33, F36, F37; §10.2)."""

from __future__ import annotations

import uuid
from collections import defaultdict

from sqlalchemy import Engine, text

from mulenetx.analytics.projection import Projection
from mulenetx.features.encoding import UNAVAILABLE, Value, observed
from mulenetx.features.registry import FEATURE_REGIME, RISK_DERIVED

GRAPH_IDS = ("F11", "F12", "F13", "F14", "F15", "F16", "F17", "F18")


def risk_derived(regime: str) -> dict[str, Value]:
    if regime != FEATURE_REGIME:
        raise NotImplementedError(f"feature regime {regime} is not implemented (PLAN T15)")
    return dict.fromkeys(RISK_DERIVED, UNAVAILABLE)


def community_densities(projection: Projection, membership: dict[str, str]) -> dict[str, float]:
    """F18: 2E / (N(N−1)) of each community in the undirected simple projection; 0 if N < 2."""
    size: dict[str, int] = defaultdict(int)
    for community in membership.values():
        size[community] += 1
    undirected = {tuple(sorted((p.source, p.destination))) for p in projection.pairs if p.source != p.destination}
    edges: dict[str, int] = defaultdict(int)
    for a, b in undirected:
        ca, cb = membership.get(a), membership.get(b)
        if ca is not None and ca == cb:
            edges[ca] += 1
    out: dict[str, float] = {}
    for community, n in size.items():
        out[community] = 0.0 if n < 2 else 2.0 * edges[community] / (n * (n - 1))
    return out


def load_graph_features(
    engine: Engine, analytics_run_id: uuid.UUID, projection: Projection, accounts: list[str]
) -> dict[str, dict[str, Value]]:
    """F11–F18 per account; accounts absent from the snapshot projection get UNAVAILABLE (cold start)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT account_id, degree, in_degree, out_degree, pagerank_norm, betweenness_raw, component_size, "
                "community_id, community_size FROM account_graph_metrics WHERE analytics_run_id = :r"
            ),
            {"r": analytics_run_id},
        ).all()
    metrics = {r.account_id: r for r in rows}
    membership = {r.account_id: r.community_id for r in rows}
    density = community_densities(projection, membership)
    out: dict[str, dict[str, Value]] = {}
    for account in accounts:
        r = metrics.get(account)
        if r is None:
            out[account] = dict.fromkeys(GRAPH_IDS, UNAVAILABLE)
            continue
        out[account] = {
            "F11": observed(r.degree, True),
            "F12": observed(r.in_degree, True),
            "F13": observed(r.out_degree, True),
            "F14": observed(float(r.pagerank_norm), True),
            "F15": observed(r.betweenness_raw, True),
            "F16": observed(r.component_size, True),
            "F17": observed(r.community_size, True),
            "F18": observed(density[r.community_id], True),
        }
    return out
