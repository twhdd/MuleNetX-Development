"""FeatureService (SRS §10, §18.1): feature vectors at an event-time cutoff T, persisted with states and lineage.

Transactional features read only transactions with timestamp ≤ T. Graph features use the latest READY
snapshot of the dataset with data_cutoff ≤ T and its analytics run (§10.4); a snapshot after T is rejected.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from mulenetx.analytics.projection import Projection, export
from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.lineage import AnalyticsRun, FeatureVersion, GraphSnapshot
from mulenetx.features import registry as registry_module
from mulenetx.features.encoding import UNAVAILABLE, Value, encode
from mulenetx.features.events import Event
from mulenetx.features.flow_features import adjacency, flow_features
from mulenetx.features.graph_features import load_graph_features, risk_derived
from mulenetx.features.registry import FEATURE_REGIME, Registry
from mulenetx.features.temporal import (
    OutIndex,
    build_out_index,
    cyclic_activity_score,
    dormancy_to_activity,
    rapid_in_out_ratio,
    short_lived_activity_score,
)
from mulenetx.features.transactional import compute as transactional

CHUNK = 5000
FEATURE_SNAPSHOT_NAMESPACE = uuid.UUID("6f1c2a3e-5b7d-4e0a-9c1f-2d8b4a6e0f13")


class SnapshotAfterCutoffError(AppError):
    def __init__(self) -> None:
        super().__init__(
            ec.VALIDATION_ERROR,
            "The graph snapshot's data_cutoff is after the feature cutoff T.",
            {"field": "graph_snapshot_id"},
        )


def feature_snapshot_id(analytics_run_id: uuid.UUID, feature_version: str, as_of: datetime) -> uuid.UUID:
    """Deterministic per (analytics run, feature version, T) so a retried FEATURES stage reuses it (OQ-44)."""
    return uuid.uuid5(
        FEATURE_SNAPSHOT_NAMESPACE, f"feature-snapshot|{analytics_run_id}|{feature_version}|{as_of.isoformat()}"
    )


@dataclass(frozen=True)
class GraphContext:
    snapshot: GraphSnapshot
    analytics_run: AnalyticsRun


def ensure_feature_version(db: Session, reg: Registry) -> None:
    """Register feature_version v1 with the registry file's hash; refuse a changed file under the same version."""
    db.execute(
        insert(FeatureVersion)
        .values(
            feature_version=reg.feature_version,
            definition_hash=reg.definition_hash,
            feature_count=len(reg.features),
            feature_registry_reference=registry_module.REGISTRY_REFERENCE,
            created_at=utcnow(),
        )
        .on_conflict_do_nothing()
    )
    row = db.get(FeatureVersion, reg.feature_version)
    if row is None or row.definition_hash != reg.definition_hash:
        raise RuntimeError("feature registry file changed without a new feature_version (SRS §10.5)")


def usable_graph_context(db: Session, dataset_id: uuid.UUID, cutoff: datetime) -> GraphContext | None:
    """Latest READY snapshot with data_cutoff ≤ T (any purpose) and its latest SUCCEEDED analytics run."""
    rows = db.execute(
        select(GraphSnapshot)
        .where(
            GraphSnapshot.dataset_id == dataset_id, GraphSnapshot.status == "READY", GraphSnapshot.data_cutoff <= cutoff
        )
        .order_by(GraphSnapshot.data_cutoff.desc(), GraphSnapshot.created_at.desc())
    ).scalars()
    for snap in rows:
        run = db.execute(
            select(AnalyticsRun)
            .where(AnalyticsRun.graph_snapshot_id == snap.graph_snapshot_id, AnalyticsRun.status == "SUCCEEDED")
            .order_by(AnalyticsRun.started_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if run is not None:
            return GraphContext(snap, run)
    return None


def _events_for_chunk(
    engine: Engine, dataset_id: uuid.UUID, cutoff: datetime, chunk: list[str]
) -> dict[str, list[Event]]:
    out: dict[str, list[Event]] = {a: [] for a in chunk}
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT transaction_id, source_account_id AS src, destination_account_id AS dst, amount,
                       EXTRACT(EPOCH FROM "timestamp")::bigint AS ts, transaction_type
                FROM transactions
                WHERE dataset_id = :d AND "timestamp" <= :c
                  AND (source_account_id = ANY(:chunk) OR destination_account_id = ANY(:chunk))
                ORDER BY "timestamp", transaction_id
                """
            ),
            {"d": dataset_id, "c": cutoff, "chunk": chunk},
        )
        for r in rows:
            amount = float(r.amount)
            if r.src in out:
                out[r.src].append(
                    Event(int(r.ts), r.transaction_id, amount, r.transaction_type, r.src == r.dst, True, r.dst)
                )
            if r.dst in out and r.dst != r.src:
                out[r.dst].append(Event(int(r.ts), r.transaction_id, amount, r.transaction_type, True, False, r.src))
    return out


def _out_index(engine: Engine, dataset_id: uuid.UUID, cutoff: datetime, window: int) -> OutIndex:
    with engine.connect() as conn:
        rows = [
            (int(r.ts), r.transaction_id, r.src, r.dst)
            for r in conn.execute(
                text(
                    """
                    SELECT EXTRACT(EPOCH FROM "timestamp")::bigint AS ts, transaction_id,
                           source_account_id AS src, destination_account_id AS dst
                    FROM transactions
                    WHERE dataset_id = :d AND "timestamp" <= :c AND "timestamp" > :c - make_interval(secs => :w)
                    ORDER BY "timestamp", transaction_id
                    """
                ),
                {"d": dataset_id, "c": cutoff, "w": window},
            )
        ]
    return build_out_index(rows, int(cutoff.timestamp()), window)


@dataclass
class FeatureVector:
    account_id: str
    values: list[float]
    states: list[int]


class FeatureService:
    def __init__(self, runtime: Runtime, reg: Registry | None = None) -> None:
        self.rt = runtime
        self.reg = reg or registry_module.load()

    def accounts_with_history(self, dataset_id: uuid.UUID, cutoff: datetime) -> list[str]:
        with self.rt.engine.connect() as conn:
            return [
                r[0]
                for r in conn.execute(
                    text(
                        """
                        SELECT account_id FROM (
                            SELECT source_account_id AS account_id FROM transactions
                            WHERE dataset_id = :d AND "timestamp" <= :c
                            UNION SELECT destination_account_id FROM transactions
                            WHERE dataset_id = :d AND "timestamp" <= :c) x
                        ORDER BY account_id
                        """
                    ),
                    {"d": dataset_id, "c": cutoff},
                )
            ]

    def vectors(
        self,
        dataset_id: uuid.UUID,
        cutoff: datetime,
        accounts: list[str],
        graph: GraphContext | None,
        check: Callable[[], None] | None = None,
    ) -> Iterator[FeatureVector]:
        """Feature vectors at T (registry order). Yields in the order of `accounts`."""
        if graph is not None and graph.snapshot.data_cutoff > cutoff:
            raise SnapshotAfterCutoffError()
        reg = self.reg
        t = int(cutoff.timestamp())
        s = self.rt.settings
        projection: Projection | None = None
        adj: dict[str, list[str]] = {}
        graph_values: dict[str, dict[str, Value]] = {}
        if graph is not None:
            projection = export(self.rt.engine, dataset_id, graph.snapshot.data_cutoff)
            adj = adjacency(projection)
            graph_values = load_graph_features(
                self.rt.engine, graph.analytics_run.analytics_run_id, projection, accounts
            )
        in_snapshot = set(projection.nodes) if projection is not None else set()
        index = _out_index(self.rt.engine, dataset_id, cutoff, reg.window("F29"))
        unavailable_risk = risk_derived(FEATURE_REGIME)
        cap32 = int(reg.cap("F32"))
        depth = int(reg.parameters["outgoing_path_max_depth"])
        for start in range(0, len(accounts), CHUNK):
            chunk = accounts[start : start + CHUNK]
            events = _events_for_chunk(self.rt.engine, dataset_id, cutoff, chunk)
            for account in chunk:
                ev = events[account]
                values: dict[str, Value] = transactional(ev, t, reg)
                values["F27"] = dormancy_to_activity(ev, t, reg)
                values["F28"] = rapid_in_out_ratio(ev, t, reg)
                values["F29"] = cyclic_activity_score(account, ev, index, t, reg, s.analytic_max_expansions)
                values["F30"] = short_lived_activity_score(ev, t, reg)
                values.update(unavailable_risk)
                if graph is None:
                    for fid in ("F11", "F12", "F13", "F14", "F15", "F16", "F17", "F18", "F32", "F34"):
                        values[fid] = UNAVAILABLE
                else:
                    values.update(graph_values[account])
                    values.update(flow_features(adj, account, account in in_snapshot, depth, cap32))
                ordered = [values[fid] for fid in reg.ids]
                floats, states = encode(ordered)
                yield FeatureVector(account, floats, states)
            if check is not None:
                check()

    def generate(
        self,
        dataset_id: uuid.UUID,
        cutoff: datetime,
        graph: GraphContext,
        accounts: list[str] | None = None,
        check: Callable[[], None] | None = None,
    ) -> uuid.UUID:
        """Compute and persist one feature generation (one COPY transaction); returns feature_snapshot_id."""
        if graph.snapshot.data_cutoff > cutoff:
            raise SnapshotAfterCutoffError()
        with self.rt.session_factory() as db:
            ensure_feature_version(db, self.reg)
            db.commit()
        fsid = feature_snapshot_id(graph.analytics_run.analytics_run_id, self.reg.feature_version, cutoff)
        population = accounts if accounts is not None else self.accounts_with_history(dataset_id, cutoff)
        now = utcnow()
        raw = self.rt.engine.raw_connection()
        try:
            cur = raw.cursor()
            cur.execute("SELECT purge_feature_snapshot(%s)", (fsid,))
            with cur.copy(
                "COPY account_feature_values (feature_snapshot_id, account_id, as_of, feature_version, "
                "graph_snapshot_id, analytics_run_id, feature_values, feature_states, created_at) FROM STDIN"
            ) as copy:
                for vec in self.vectors(dataset_id, cutoff, population, graph, check):
                    copy.write_row(
                        (
                            fsid,
                            vec.account_id,
                            cutoff,
                            self.reg.feature_version,
                            graph.snapshot.graph_snapshot_id,
                            graph.analytics_run.analytics_run_id,
                            vec.values,
                            vec.states,
                            now,
                        )
                    )
            raw.commit()
        except BaseException:
            raw.rollback()
            raise
        finally:
            raw.close()
        return fsid
