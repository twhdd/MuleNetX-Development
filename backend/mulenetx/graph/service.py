"""GraphService: Neo4j snapshot build, validation, retirement (SRS §6.8, §18.1)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import func, select

from mulenetx.core import ids
from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import isoformat_utc, utcnow
from mulenetx.db.models.canonical import Transaction
from mulenetx.db.models.lineage import GraphSnapshot
from mulenetx.graph.build import GraphBuilder
from mulenetx.graph.retire import delete_snapshot_data
from mulenetx.graph.validate import expected_from_postgres, validate

logger = logging.getLogger("mulenetx.graph")

PIPELINE_VERSION = "graph-build-v1"
GRAPH_SCHEMA_VERSION = "neo4j-schema-v1"


def snapshot_id_for(dataset_id: uuid.UUID, purpose: str, cutoff: datetime) -> uuid.UUID:
    return ids.graph_snapshot_id(dataset_id, purpose, isoformat_utc(cutoff), PIPELINE_VERSION, GRAPH_SCHEMA_VERSION)


def operational_snapshot_id(dataset_id: uuid.UUID, cutoff: datetime) -> uuid.UUID:
    return snapshot_id_for(dataset_id, "OPERATIONAL", cutoff)


class GraphValidationMismatchError(Exception):
    def __init__(self, mismatches: list[str]) -> None:
        super().__init__(", ".join(mismatches))
        self.mismatches = mismatches


class GraphService:
    def __init__(self, runtime: Runtime) -> None:
        self.rt = runtime

    def prepare_snapshot(
        self, dataset_id: uuid.UUID, ingestion_run_id: uuid.UUID, purpose: str, bound: datetime
    ) -> GraphSnapshot | None:
        """The snapshot of all transactions with timestamp ≤ `bound`: data_cutoff = their maximum timestamp
        (§3.4 rule 2); ID derived from content (OQ-37). None if there is no such transaction."""
        with self.rt.session_factory() as db:
            cutoff = db.execute(
                select(func.max(Transaction.timestamp)).where(
                    Transaction.dataset_id == dataset_id, Transaction.timestamp <= bound
                )
            ).scalar_one()
        if cutoff is None:
            return None
        return self.create_snapshot_row(
            snapshot_id_for(dataset_id, purpose, cutoff), dataset_id, ingestion_run_id, purpose, cutoff
        )

    def create_snapshot_row(
        self,
        snapshot_id: uuid.UUID,
        dataset_id: uuid.UUID,
        ingestion_run_id: uuid.UUID,
        purpose: str,
        cutoff: datetime,
    ) -> GraphSnapshot:
        with self.rt.session_factory() as db:
            existing = db.get(GraphSnapshot, snapshot_id)
            if existing is not None:
                return existing
            count = db.execute(
                select(func.count())
                .select_from(Transaction)
                .where(Transaction.dataset_id == dataset_id, Transaction.timestamp <= cutoff)
            ).scalar_one()
            snap = GraphSnapshot(
                graph_snapshot_id=snapshot_id,
                dataset_id=dataset_id,
                ingestion_run_id=ingestion_run_id,
                purpose=purpose,
                data_cutoff=cutoff,
                pipeline_version=PIPELINE_VERSION,
                graph_schema_version=GRAPH_SCHEMA_VERSION,
                source_record_count=int(count),
                status="BUILDING",
                created_at=utcnow(),
            )
            db.add(snap)
            db.commit()
            return snap

    def _set_status(self, snapshot_id: uuid.UUID, status: str) -> None:
        with self.rt.session_factory() as db:
            snap = db.get(GraphSnapshot, snapshot_id, with_for_update=True)
            assert snap is not None
            snap.status = status
            db.commit()

    def build_and_validate(self, snapshot_id: uuid.UUID, check: Callable[[], None] | None = None) -> GraphSnapshot:
        """Delete any partial data of the snapshot, rebuild, validate; READY on success (§6.8.2–§6.8.4)."""
        with self.rt.session_factory() as db:
            snap = db.get(GraphSnapshot, snapshot_id)
            assert snap is not None
            if snap.status == "READY":
                return snap
            dataset_id, cutoff = snap.dataset_id, snap.data_cutoff
        s = self.rt.settings
        self._set_status(snapshot_id, "BUILDING")
        delete_snapshot_data(self.rt.graph, snapshot_id, s.graph_build_batch_size, check)
        GraphBuilder(self.rt.engine, self.rt.graph, s.graph_build_batch_size, check).build(
            snapshot_id, dataset_id, cutoff
        )
        self._set_status(snapshot_id, "VALIDATING")
        expected = expected_from_postgres(self.rt.engine, dataset_id, cutoff)
        result = validate(self.rt.graph, snapshot_id, expected)
        with self.rt.session_factory() as db:
            snap = db.get(GraphSnapshot, snapshot_id, with_for_update=True)
            assert snap is not None
            if not result.ok:
                snap.status = "FAILED"
                db.commit()
                logger.error("graph validation mismatch for %s: %s", snapshot_id, result.mismatches)
                raise GraphValidationMismatchError(result.mismatches)
            snap.status = "READY"
            snap.node_count = result.node_count
            snap.edge_count = result.edge_count
            snap.validation_digest = result.digest
            if snap.ready_at is None:  # a re-materialized (previously retired) snapshot keeps its first ready_at
                snap.ready_at = utcnow()
            db.commit()
            return snap

    def mark_failed(self, snapshot_id: uuid.UUID) -> None:
        with self.rt.session_factory() as db:
            snap = db.get(GraphSnapshot, snapshot_id, with_for_update=True)
            if snap is not None and snap.status in ("BUILDING", "VALIDATING"):
                snap.status = "FAILED"
                db.commit()

    def retire(self, snapshot_id: uuid.UUID, check: Callable[[], None] | None = None) -> None:
        """Delete the snapshot's Neo4j data in batches and mark it RETIRED (§6.8.6)."""
        delete_snapshot_data(self.rt.graph, snapshot_id, self.rt.settings.graph_build_batch_size, check)
        with self.rt.session_factory() as db:
            snap = db.get(GraphSnapshot, snapshot_id, with_for_update=True)
            if snap is not None and snap.status != "RETIRED":
                snap.status = "RETIRED"
                db.commit()
