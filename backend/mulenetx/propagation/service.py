"""PropagationService (SRS §13): adjacency of the scoring run's snapshot and the bounded propagation."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Engine, text

from mulenetx.core.decimal import D
from mulenetx.propagation.bfs import Contribution, propagate, undirected_adjacency


def snapshot_pairs(engine: Engine, dataset_id: uuid.UUID, cutoff: datetime) -> list[tuple[str, str]]:
    with engine.connect() as conn:
        return [
            (r.src, r.dst)
            for r in conn.execute(
                text(
                    "SELECT DISTINCT source_account_id AS src, destination_account_id AS dst FROM transactions "
                    'WHERE dataset_id = :d AND "timestamp" <= :c ORDER BY 1, 2'
                ),
                {"d": dataset_id, "c": cutoff},
            )
        ]


def run_propagation(
    engine: Engine, dataset_id: uuid.UUID, cutoff: datetime, pre_scores: dict[str, Decimal], params: dict[str, Any]
) -> dict[str, list[Contribution]]:
    adjacency = undirected_adjacency(snapshot_pairs(engine, dataset_id, cutoff))
    threshold = D(params["source_threshold"])
    return propagate(
        adjacency,
        pre_scores,
        threshold,
        int(params["maximum_distance"]),
        D(params["maximum_contribution"]),
        int(params["provenance_top_n"]),
    )
