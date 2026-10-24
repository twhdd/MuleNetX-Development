"""Batched deletion of a snapshot's Neo4j data (retry §6.8.3 and retirement §6.8.6)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from mulenetx.graph import cypher
from mulenetx.graph.neo4j_client import Neo4jClient


def delete_snapshot_data(
    graph: Neo4jClient, snapshot_id: uuid.UUID, batch: int, check: Callable[[], None] | None = None
) -> int:
    deleted = 0
    for statement in (cypher.DELETE_TRANSACTIONS_BATCH, cypher.DELETE_ACCOUNTS_BATCH):
        while True:
            n = int(graph.run(statement, {"sid": str(snapshot_id), "batch": batch})[0]["n"])
            deleted += n
            if check is not None:
                check()
            if n == 0:
                break
    return deleted
