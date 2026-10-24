"""Snapshot validation (SRS §6.8.4): counts, amounts and a transaction-ID digest against PostgreSQL."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Engine, text

from mulenetx.graph import cypher
from mulenetx.graph.build import MICROS
from mulenetx.graph.neo4j_client import Neo4jClient


def digest(transaction_ids: Iterable[str]) -> str:
    """SHA-256 over the ascending transaction IDs, each terminated by a newline."""
    h = hashlib.sha256()
    for tid in sorted(transaction_ids):
        h.update(tid.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


@dataclass(frozen=True)
class Expected:
    accounts: int
    transactions: int
    pairs: int
    amount_micros: int
    digest: str


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    mismatches: list[str]
    node_count: int
    edge_count: int
    digest: str


def expected_from_postgres(engine: Engine, dataset_id: uuid.UUID, cutoff: datetime) -> Expected:
    p = {"d": dataset_id, "c": cutoff}
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT count(*) AS n, coalesce(sum(amount), 0) AS total,
                       count(DISTINCT (source_account_id, destination_account_id)) AS pairs
                FROM transactions WHERE dataset_id = :d AND "timestamp" <= :c
                """
            ),
            p,
        ).one()
        accounts = conn.execute(
            text(
                """
                SELECT count(*) FROM (
                    SELECT source_account_id FROM transactions WHERE dataset_id = :d AND "timestamp" <= :c
                    UNION SELECT destination_account_id FROM transactions WHERE dataset_id = :d AND "timestamp" <= :c
                ) x
                """
            ),
            p,
        ).scalar_one()
        ids = (
            r[0]
            for r in conn.execution_options(stream_results=True).execute(
                text('SELECT transaction_id FROM transactions WHERE dataset_id = :d AND "timestamp" <= :c'), p
            )
        )
        pg_digest = digest(ids)
    total: Decimal = row.total
    return Expected(
        int(accounts), int(row.n), int(row.pairs), int(total.quantize(Decimal("0.000001")) * MICROS), pg_digest
    )


def validate(graph: Neo4jClient, snapshot_id: uuid.UUID, expected: Expected) -> ValidationResult:
    sid = {"sid": str(snapshot_id)}
    accounts = int(graph.run(cypher.COUNT_ACCOUNTS, sid)[0]["n"])
    transactions = int(graph.run(cypher.COUNT_TRANSACTIONS, sid)[0]["n"])
    totals = graph.run(cypher.TRANSFER_TOTALS, sid)[0]
    pairs, micros = int(totals["n"]), int(totals["micros"])
    neo_digest = digest(r["id"] for r in graph.run(cypher.TRANSACTION_IDS, sid))
    mismatches = [
        name
        for name, ok in (
            ("account_count", accounts == expected.accounts),
            ("transaction_count", transactions == expected.transactions),
            ("transferred_to_count", pairs == expected.pairs),
            ("total_amount", micros == expected.amount_micros),
            ("validation_digest", neo_digest == expected.digest),
        )
        if not ok
    ]
    return ValidationResult(not mismatches, mismatches, accounts + transactions, pairs, neo_digest)
