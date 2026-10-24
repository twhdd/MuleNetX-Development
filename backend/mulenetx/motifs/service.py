"""TemporalMotifService (SRS §15.9, §18.1): detection over all transactions of a snapshot, run inside the
ANALYTICS stage and persisted with the analytics run."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text

from mulenetx.core import ids
from mulenetx.core.config import Settings
from mulenetx.motifs.burst import detect_bursts
from mulenetx.motifs.common import DETECTOR_VERSION, Index, Instance, MTx
from mulenetx.motifs.confidence import PARAMETERS
from mulenetx.motifs.fan import detect_fans
from mulenetx.motifs.paths import detect_path_motifs


def configuration(settings: Settings) -> dict[str, Any]:
    """Detector parameters recorded in the analytics run's `algorithm_configuration` (part of `analytics_version`)."""
    return {
        "detector_version": DETECTOR_VERSION,
        "max_depth": settings.analytic_max_depth,
        "max_expansions_per_anchor": settings.motif_max_expansions_per_anchor,
        "rapid_pass_through": {"hops": [2, 5], "max_gap_seconds": 900},
        "fan": {"window_seconds": 3600, "min_counterparties": 3, "segmentation": "greedy non-overlapping"},
        "circular_flow": {"hops": [3, 5], "max_span_seconds": 86_400},
        "layered_movement": {"hops": [4, 5], "max_span_seconds": 86_400},
        "burst_activity": {"bucket_seconds": 3600, "baseline_buckets": 168, "min_count": 5, "multiplier": 3},
        "confidence_parameters": {k: list(v) for k, v in PARAMETERS.items()},
    }


def load_transactions(engine: Engine, dataset_id: uuid.UUID, cutoff: datetime) -> list[MTx]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT transaction_id, source_account_id AS src, destination_account_id AS dst, amount,
                       EXTRACT(EPOCH FROM "timestamp")::bigint AS ts
                FROM transactions WHERE dataset_id = :d AND "timestamp" <= :c
                ORDER BY "timestamp", transaction_id
                """
            ),
            {"d": dataset_id, "c": cutoff},
        )
        return [MTx(int(r.ts), r.transaction_id, r.src, r.dst, r.amount) for r in rows]


def detect(txs: list[MTx], settings: Settings) -> list[Instance]:
    """All six detectors; identical instances (same type, window, transaction set) collapse (§15.9.8)."""
    index = Index(txs)
    found = detect_path_motifs(index, settings.analytic_max_depth, settings.motif_max_expansions_per_anchor)
    found += detect_fans(index)
    found += detect_bursts(index)
    unique: dict[tuple[str, int, tuple[str, ...]], Instance] = {}
    for inst in found:
        unique.setdefault((inst.motif_type, inst.window_seconds, tuple(sorted(inst.tx_ids))), inst)
    return list(unique.values())


def _iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, UTC).isoformat().replace("+00:00", "Z")


def to_row(
    inst: Instance, snapshot_id: uuid.UUID, analytics_run_id: uuid.UUID, version: str, now: datetime
) -> tuple[Any, ...]:
    motif_id = ids.motif_id(snapshot_id, version, inst.motif_type, inst.window_seconds, inst.tx_ids)
    evidence = {
        "selected_transactions": list(inst.tx_ids),
        "participating_accounts": inst.accounts,
        "timestamps": [_iso(t.ts) for t in inst.transactions],
        "components": inst.components,
        "confidence": format(inst.confidence, "f"),
        "order_ambiguous": inst.order_ambiguous,
        "truncated": inst.truncated,
        "detector_version": DETECTOR_VERSION,
        "statement": "A motif is an analytical pattern, not a criminality classification.",
    }
    return (
        motif_id,
        analytics_run_id,
        snapshot_id,
        inst.motif_type,
        inst.anchor,
        datetime.fromtimestamp(inst.start, UTC),
        datetime.fromtimestamp(inst.end, UTC),
        inst.window_seconds,
        inst.accounts,
        list(inst.tx_ids),
        len(inst.transactions),
        inst.confidence,
        inst.order_ambiguous,
        evidence,
        version,
        now,
    )
