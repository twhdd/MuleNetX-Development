"""Snapshot build (SRS §6.8.2): accounts, then transactions, in ascending canonical ID order, in idempotent
`UNWIND … MERGE` batches; then `TRANSFERRED_TO` aggregates from the loaded transactions."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Engine, text

from mulenetx.graph import cypher
from mulenetx.graph.neo4j_client import Neo4jClient

MICROS = Decimal(1_000_000)


def snapshot_key(snapshot_id: uuid.UUID, canonical_id: str) -> str:
    return f"{snapshot_id}:{canonical_id}"


class GraphBuilder:
    def __init__(self, engine: Engine, graph: Neo4jClient, batch_size: int, check: Callable[[], None] | None = None):
        self.engine = engine
        self.graph = graph
        self.batch_size = batch_size
        self.check = check or (lambda: None)

    def build(self, snapshot_id: uuid.UUID, dataset_id: uuid.UUID, cutoff: datetime) -> None:
        self._accounts(snapshot_id, dataset_id, cutoff)
        self._transactions(snapshot_id, dataset_id, cutoff)
        self._transfers(snapshot_id, dataset_id, cutoff)

    def _accounts(self, sid: uuid.UUID, dataset_id: uuid.UUID, cutoff: datetime) -> None:
        sql = text(
            """
            SELECT a.account_id, a.account_type FROM accounts a
            WHERE a.account_id IN (
                SELECT source_account_id FROM transactions WHERE dataset_id = :d AND "timestamp" <= :c
                UNION SELECT destination_account_id FROM transactions WHERE dataset_id = :d AND "timestamp" <= :c)
            ORDER BY a.account_id
            """
        )
        with self.engine.connect() as conn:
            result = conn.execution_options(stream_results=True, max_row_buffer=self.batch_size).execute(
                sql, {"d": dataset_id, "c": cutoff}
            )
            for batch in result.partitions(self.batch_size):
                rows = [
                    {"key": snapshot_key(sid, r.account_id), "account_id": r.account_id, "account_type": r.account_type}
                    for r in batch
                ]
                self.graph.run(cypher.MERGE_ACCOUNTS, {"rows": rows, "sid": str(sid), "dataset_id": str(dataset_id)})
                self.check()

    def write_transaction_batch(self, sid: uuid.UUID, rows: list[dict[str, object]]) -> None:
        self.graph.run(cypher.MERGE_TRANSACTIONS, {"rows": rows, "sid": str(sid)})

    def _transactions(self, sid: uuid.UUID, dataset_id: uuid.UUID, cutoff: datetime) -> None:
        sql = text(
            """
            SELECT transaction_id, source_account_id, destination_account_id, amount, "timestamp",
                   transaction_type
            FROM transactions WHERE dataset_id = :d AND "timestamp" <= :c ORDER BY transaction_id
            """
        )
        with self.engine.connect() as conn:
            result = conn.execution_options(stream_results=True, max_row_buffer=self.batch_size).execute(
                sql, {"d": dataset_id, "c": cutoff}
            )
            for batch in result.partitions(self.batch_size):
                rows: list[dict[str, object]] = [
                    {
                        "key": snapshot_key(sid, r.transaction_id),
                        "transaction_id": r.transaction_id,
                        "amount": float(r.amount),
                        "amount_micros": int(r.amount * MICROS),
                        "timestamp": r.timestamp,
                        "transaction_type": r.transaction_type,
                        "source_key": snapshot_key(sid, r.source_account_id),
                        "destination_key": snapshot_key(sid, r.destination_account_id),
                    }
                    for r in batch
                ]
                self.write_transaction_batch(sid, rows)
                self.check()

    def _transfers(self, sid: uuid.UUID, dataset_id: uuid.UUID, cutoff: datetime) -> None:
        sql = text(
            """
            SELECT DISTINCT source_account_id FROM transactions
            WHERE dataset_id = :d AND "timestamp" <= :c ORDER BY source_account_id
            """
        )
        with self.engine.connect() as conn:
            result = conn.execution_options(stream_results=True, max_row_buffer=self.batch_size).execute(
                sql, {"d": dataset_id, "c": cutoff}
            )
            for batch in result.partitions(self.batch_size):
                keys = [snapshot_key(sid, r.source_account_id) for r in batch]
                self.graph.run(cypher.MERGE_TRANSFERS, {"keys": keys, "sid": str(sid)})
                self.check()
