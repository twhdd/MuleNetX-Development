"""Deterministic analytical identifiers (SRS §6.2.3).

Each function builds the canonical content string exactly as the §6.2.3 table writes it
(fields joined with `|`, lists sorted ascending and joined with `,`) and returns UUIDv5 under the
fixed namespace. Ordered lists (path account sequences) keep their order.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence

NAMESPACE = uuid.UUID("6f1c2a3e-5b7d-4e0a-9c1f-2d8b4a6e0f13")


def _uuid5(content: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, content)


def _sorted_list(values: Iterable[str]) -> str:
    return ",".join(sorted(values))


def community_id(graph_snapshot_id: uuid.UUID | str, analytics_version: str, member_account_ids: Iterable[str]) -> str:
    """`community|{graph_snapshot_id}|{analytics_version}|{sorted member account_ids}`; stored as text."""
    content = f"community|{graph_snapshot_id}|{analytics_version}|{_sorted_list(member_account_ids)}"
    return str(_uuid5(content))


def candidate_id(graph_snapshot_id: uuid.UUID | str, scoring_run_id: uuid.UUID | str, community_id: str) -> uuid.UUID:
    """`candidate|{graph_snapshot_id}|{scoring_run_id}|{community_id}`; also the ring_id."""
    return _uuid5(f"candidate|{graph_snapshot_id}|{scoring_run_id}|{community_id}")


def motif_id(
    graph_snapshot_id: uuid.UUID | str,
    analytics_version: str,
    motif_type: str,
    temporal_window_seconds: int,
    transaction_ids: Iterable[str],
) -> uuid.UUID:
    """`motif|{graph_snapshot_id}|{analytics_version}|{motif_type}|{window}|{sorted transaction_ids}`."""
    content = (
        f"motif|{graph_snapshot_id}|{analytics_version}|{motif_type}|{temporal_window_seconds}|"
        f"{_sorted_list(transaction_ids)}"
    )
    return _uuid5(content)


def path_id(graph_snapshot_id: uuid.UUID | str, ordered_account_ids: Sequence[str]) -> uuid.UUID:
    """`path|{graph_snapshot_id}|{ordered account_ids}` (order preserved)."""
    return _uuid5(f"path|{graph_snapshot_id}|{','.join(ordered_account_ids)}")


def intervention_candidate_id(
    baseline_graph_snapshot_id: uuid.UUID | str,
    scoring_run_id: uuid.UUID | str,
    target_ring_id: uuid.UUID | str,
    operation_type: str,
    target_ids: Iterable[str],
    ranking_configuration_hash: str,
) -> uuid.UUID:
    """`intervention|{baseline}|{scoring_run}|{ring}|{operation}|{sorted target_ids}|{config hash}`."""
    content = (
        f"intervention|{baseline_graph_snapshot_id}|{scoring_run_id}|{target_ring_id}|{operation_type}|"
        f"{_sorted_list(target_ids)}|{ranking_configuration_hash}"
    )
    return _uuid5(content)


def reference_ring_id(reference_construction_version: str, member_account_ids: Iterable[str]) -> uuid.UUID:
    """`refring|{reference_construction_version}|{sorted member account_ids}`."""
    return _uuid5(f"refring|{reference_construction_version}|{_sorted_list(member_account_ids)}")


def graph_snapshot_id(
    dataset_id: uuid.UUID | str, purpose: str, data_cutoff: str, pipeline_version: str, graph_schema_version: str
) -> uuid.UUID:
    """`snapshot|{dataset_id}|{purpose}|{data_cutoff}|{pipeline_version}|{graph_schema_version}` (OQ-37).

    Not in the §6.2.3 table: identical inputs and versions yield the identical snapshot, which §25.5 needs
    for identical community, motif and path identifiers on rerun."""
    return _uuid5(f"snapshot|{dataset_id}|{purpose}|{data_cutoff}|{pipeline_version}|{graph_schema_version}")
