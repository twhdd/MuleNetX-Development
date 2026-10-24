"""Community detection (SRS §8.3): Louvain on the undirected weighted simple projection, resolution 1.0,
seed 42, with canonical community IDs (§6.2.3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import networkx as nx

from mulenetx.analytics.projection import Projection
from mulenetx.core import ids


@dataclass(frozen=True)
class Community:
    community_id: str
    members: tuple[str, ...]


def louvain(proj: Projection, resolution: float, seed: int) -> list[list[str]]:
    g = proj.undirected_weighted()
    if g.number_of_nodes() == 0:
        return []
    parts = nx.community.louvain_communities(g, weight="weight", resolution=resolution, seed=seed)
    return sorted((sorted(p) for p in parts), key=lambda members: members[0])


def canonical_communities(
    proj: Projection, snapshot_id: uuid.UUID, analytics_version: str, resolution: float, seed: int
) -> list[Community]:
    return [
        Community(ids.community_id(snapshot_id, analytics_version, members), tuple(members))
        for members in louvain(proj, resolution, seed)
    ]
