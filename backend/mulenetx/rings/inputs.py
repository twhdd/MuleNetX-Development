"""Inputs of community and ring computations for one analytical context (snapshot, analytics run, scoring run).

Pure data, so the §9/§9A computations can run on fixtures without a database; `load` builds them from
PostgreSQL."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Engine, text

from mulenetx.core.percentile import percentile_rank
from mulenetx.flow.analytic_paths import AnalyticProjection, Budget, Tx, load_projection
from mulenetx.flow.vocabulary import ScoringContext, load_context


@dataclass(frozen=True)
class MotifRef:
    motif_type: str
    anchor: str
    accounts: frozenset[str]
    transaction_ids: frozenset[str]


@dataclass
class ContextInputs:
    run: ScoringContext
    projection: AnalyticProjection
    pagerank_pct: dict[str, float]
    betweenness_pct: dict[str, float]
    motifs: list[MotifRef]
    budget: Budget
    communities: dict[str, list[str]] = field(default_factory=dict)  # community_id → members (account_id order)
    tier_thresholds: dict[str, str] = field(
        default_factory=lambda: {"LOW": "0.00", "MEDIUM": "0.25", "HIGH": "0.50", "CRITICAL": "0.75"}
    )

    def internal(self, members: set[str]) -> list[tuple[str, str, Tx]]:
        """Transactions whose source and destination are both members, in (timestamp, transaction_id) order."""
        out = [(u, v, t) for (u, v), txs in self.projection.hops.items() if u in members and v in members for t in txs]
        out += [(a, a, t) for a, txs in self.projection.loops.items() if a in members for t in txs]
        return sorted(out, key=lambda x: (x[2].timestamp, x[2].transaction_id))


def load(
    engine: Engine,
    dataset_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    data_cutoff: datetime,
    analytics_run_id: uuid.UUID,
    analytics_version: str,
    scoring_run_id: uuid.UUID,
    budget: Budget,
) -> ContextInputs:
    run = load_context(engine, scoring_run_id)
    proj = load_projection(engine, snapshot_id, dataset_id, data_cutoff)
    with engine.connect() as conn:
        metrics = conn.execute(
            text(
                "SELECT account_id, pagerank_raw, betweenness_raw FROM account_graph_metrics "
                "WHERE analytics_run_id = :r ORDER BY account_id"
            ),
            {"r": analytics_run_id},
        ).all()
        motifs = [
            MotifRef(
                r.motif_type,
                r.anchor_account_id,
                frozenset(r.participating_account_ids),
                frozenset(r.participating_transaction_ids),
            )
            for r in conn.execute(
                text(
                    "SELECT motif_type, anchor_account_id, participating_account_ids, participating_transaction_ids "
                    "FROM temporal_motifs WHERE graph_snapshot_id = :s AND analytics_version = :v"
                ),
                {"s": snapshot_id, "v": analytics_version},
            )
        ]
        thresholds = conn.execute(
            text(
                "SELECT r.tier_thresholds FROM scoring_runs s JOIN risk_logic_versions r USING (risk_logic_version) "
                "WHERE s.scoring_run_id = :r"
            ),
            {"r": scoring_run_id},
        ).scalar_one()
        communities: dict[str, list[str]] = {}
        for r in conn.execute(
            text(
                "SELECT community_id, account_id FROM community_memberships WHERE analytics_run_id = :r "
                "ORDER BY community_id, account_id"
            ),
            {"r": analytics_run_id},
        ):
            communities.setdefault(r.community_id, []).append(r.account_id)
    ids = [m.account_id for m in metrics]
    pr = dict(zip(ids, percentile_rank([float(m.pagerank_raw) for m in metrics]), strict=True))
    bt = dict(zip(ids, percentile_rank([float(m.betweenness_raw) for m in metrics]), strict=True))
    return ContextInputs(run, proj, pr, bt, motifs, budget, communities, dict(thresholds))
