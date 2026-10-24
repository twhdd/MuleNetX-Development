"""Training data construction (SRS §11.4–§11.6): split boundaries, populations with first-split entity
assignment, TRAINING_SPLIT snapshots with their analytics runs and feature generations, and labels."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from sqlalchemy import select, text

from mulenetx.analytics.service import AnalyticsService
from mulenetx.core.runtime import Runtime
from mulenetx.db.models.lineage import AnalyticsRun, GraphSnapshot
from mulenetx.features.registry import load as load_registry
from mulenetx.features.service import FeatureService, GraphContext
from mulenetx.graph.service import GraphService
from mulenetx.ml.splits import SPLITS, SplitBoundaries, compute_boundaries
from mulenetx.ml.target import EXCLUDED_ACCOUNT_TYPES, label_from_counts


@dataclass
class SplitData:
    split: str
    cutoff: datetime
    window: tuple[datetime, datetime]
    graph_snapshot_id: uuid.UUID
    snapshot_cutoff: datetime
    analytics_run_id: uuid.UUID
    feature_snapshot_id: uuid.UUID
    accounts: list[str] = field(default_factory=list)
    labels: list[int] = field(default_factory=list)
    features: np.ndarray = field(default_factory=lambda: np.zeros((0, 42)))
    states: np.ndarray = field(default_factory=lambda: np.zeros((0, 42), dtype=np.int16))
    feature_as_of: list[datetime] = field(default_factory=list)
    label_window_violations: int = 0
    exclusions: dict[str, int] = field(default_factory=dict)

    def class_distribution(self) -> dict[str, int]:
        pos = int(sum(self.labels))
        return {"observations": len(self.labels), "positive": pos, "negative": len(self.labels) - pos}


@dataclass
class TrainingData:
    dataset_id: uuid.UUID
    boundaries: SplitBoundaries
    splits: dict[str, SplitData]
    feature_version: str
    feature_ids: list[str]


def split_boundaries(rt: Runtime, dataset_id: uuid.UUID, resolution: int) -> SplitBoundaries:
    with rt.engine.connect() as conn:
        epochs = [
            int(r[0])
            for r in conn.execute(
                text(
                    'SELECT EXTRACT(EPOCH FROM "timestamp")::bigint FROM transactions WHERE dataset_id = :d '
                    'ORDER BY "timestamp"'
                ),
                {"d": dataset_id},
            )
        ]
    s = rt.settings
    return compute_boundaries(epochs, resolution, s.split_percentile_train, s.split_percentile_val)


def population(
    rt: Runtime, dataset_id: uuid.UUID, window: tuple[datetime, datetime], assigned: set[str]
) -> tuple[list[tuple[str, int | None]], dict[str, int]]:
    """Accounts with ≥ 1 transaction in W (as source or destination), with label counts from W only.
    Returns ([(account_id, label)], exclusion counts); MERCHANT and earlier-split accounts are excluded."""
    lo, hi = window
    with rt.engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT x.account_id, a.account_type, count(*) AS n,
                       count(*) FILTER (WHERE x.fraud_label IS TRUE) AS fraud,
                       count(x.fraud_label) AS labelled
                FROM (
                    SELECT source_account_id AS account_id, fraud_label FROM transactions
                    WHERE dataset_id = :d AND "timestamp" > :lo AND "timestamp" <= :hi
                    UNION ALL
                    SELECT destination_account_id, fraud_label FROM transactions
                    WHERE dataset_id = :d AND "timestamp" > :lo AND "timestamp" <= :hi
                      AND destination_account_id <> source_account_id
                ) x JOIN accounts a ON a.account_id = x.account_id
                GROUP BY x.account_id, a.account_type
                ORDER BY x.account_id
                """
            ),
            {"d": dataset_id, "lo": lo, "hi": hi},
        ).all()
    out: list[tuple[str, int | None]] = []
    excluded = {"merchant": 0, "earlier_split": 0, "unlabelled": 0}
    for r in rows:
        if r.account_type in EXCLUDED_ACCOUNT_TYPES:
            excluded["merchant"] += 1
            continue
        if r.account_id in assigned:
            excluded["earlier_split"] += 1
            continue
        y = label_from_counts(int(r.n), int(r.fraud), int(r.labelled))
        if y is None:
            excluded["unlabelled"] += 1
        out.append((r.account_id, y))
    return out, excluded


def _analytics_for(rt: Runtime, snapshot: GraphSnapshot) -> AnalyticsRun:
    with rt.session_factory() as db:
        existing = (
            db.execute(
                select(AnalyticsRun)
                .where(AnalyticsRun.graph_snapshot_id == snapshot.graph_snapshot_id, AnalyticsRun.status == "SUCCEEDED")
                .order_by(AnalyticsRun.started_at.desc())
            )
            .scalars()
            .first()
        )
    if existing is not None:
        return existing
    result = AnalyticsService(rt).run(snapshot.graph_snapshot_id, snapshot.dataset_id, snapshot.data_cutoff)
    with rt.session_factory() as db:
        run = db.get(AnalyticsRun, result.analytics_run_id)
        assert run is not None
        return run


def build(
    rt: Runtime,
    dataset_id: uuid.UUID,
    ingestion_run_id: uuid.UUID,
    resolution: int,
    check: Callable[[], None] | None = None,
) -> TrainingData:
    reg = load_registry()
    boundaries = split_boundaries(rt, dataset_id, resolution)
    graph = GraphService(rt)
    features = FeatureService(rt, reg)
    assigned: set[str] = set()
    splits: dict[str, SplitData] = {}
    for split in SPLITS:
        window = boundaries.windows()[split]
        cutoff = window[1]
        snapshot = graph.prepare_snapshot(dataset_id, ingestion_run_id, "TRAINING_SPLIT", cutoff)
        if snapshot is None:
            raise ValueError(f"no transactions at or before the {split} cutoff")
        snapshot = graph.build_and_validate(snapshot.graph_snapshot_id, check)
        analytics = _analytics_for(rt, snapshot)
        members, excluded = population(rt, dataset_id, window, assigned)
        labelled = [(a, y) for a, y in members if y is not None]
        assigned.update(a for a, _ in members)
        accounts = [a for a, _ in labelled]
        ctx = GraphContext(snapshot, analytics)
        fsid = features.generate(dataset_id, cutoff, ctx, accounts=accounts, check=check)
        data = SplitData(
            split,
            cutoff,
            window,
            snapshot.graph_snapshot_id,
            snapshot.data_cutoff,
            analytics.analytics_run_id,
            fsid,
            exclusions=excluded,
        )
        if accounts:
            with rt.engine.connect() as conn:
                rows = {
                    r.account_id: r
                    for r in conn.execute(
                        text(
                            "SELECT account_id, feature_values, feature_states, as_of FROM account_feature_values "
                            "WHERE feature_snapshot_id = :f"
                        ),
                        {"f": fsid},
                    )
                }
            data.accounts = accounts
            data.labels = [int(y) for _, y in labelled if y is not None]
            data.features = np.array([rows[a].feature_values for a in accounts], dtype=np.float64)
            data.states = np.array([rows[a].feature_states for a in accounts], dtype=np.int16)
            data.feature_as_of = [rows[a].as_of for a in accounts]
        splits[split] = data
        if check is not None:
            check()
    return TrainingData(dataset_id, boundaries, splits, reg.feature_version, reg.ids)


def label_window_audit(rt: Runtime, data: TrainingData) -> dict[str, int]:
    """Check 7 evidence: recompute each label from the raw transactions of W_k only and count mismatches."""
    from mulenetx.ml.target import label

    out: dict[str, int] = {}
    for split, s in data.splits.items():
        if not s.accounts:
            out[split] = 0
            continue
        lo, hi = s.window
        per_account: dict[str, list[bool | None]] = {a: [] for a in s.accounts}
        with rt.engine.connect() as conn:
            for r in conn.execute(
                text(
                    'SELECT source_account_id AS src, destination_account_id AS dst, fraud_label, "timestamp" AS ts '
                    "FROM transactions WHERE dataset_id = :d AND (source_account_id = ANY(:a) OR "
                    "destination_account_id = ANY(:a))"
                ),
                {"d": data.dataset_id, "a": s.accounts},
            ):
                if not (lo < r.ts <= hi):
                    continue
                for acc in {r.src, r.dst}:
                    if acc in per_account:
                        per_account[acc].append(r.fraud_label)
        out[split] = sum(1 for a, y in zip(s.accounts, s.labels, strict=True) if label(per_account[a]) != y)
    return out
