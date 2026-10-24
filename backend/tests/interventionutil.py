"""Build intervention baselines from in-memory graphs (no database)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mulenetx.flow.analytic_paths import Budget, enumerate_ring_scope
from mulenetx.interventions import ranking
from mulenetx.interventions.baseline import Baseline, build
from mulenetx.interventions.engine import Result, evaluate
from mulenetx.interventions.pool import rank_pool
from tests.flowutil import RUN, context, projection_from_edges

RING = "00000000-0000-4000-8000-00000000ee01"
CONFIG = ranking.configuration(5000, 5, 10_000, 1_000_000)
HASH = ranking.configuration_hash(CONFIG)
FIXTURE = Path(__file__).parent / "fixtures" / "network_risk_counterexample" / "expected.json"


def counterexample() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text())
    return data


def baseline(
    edges: list[list[str]] | list[tuple[str, str, str]],
    scores: dict[str, str],
    members: list[str],
    budget: Budget | None = None,
    threshold: str = "0.50",
) -> Baseline:
    proj = projection_from_edges([tuple(e) for e in edges])  # type: ignore[misc]
    run = context(scores, threshold=threshold)
    scope = enumerate_ring_scope(proj, members, run, budget or Budget())
    return build(proj, run, scope)


def counterexample_baseline() -> Baseline:
    fx = counterexample()
    return baseline(fx["edges"], fx["scores"], fx["members"])


def rank(b: Baseline, max_candidates: int = 5000) -> list[Result]:
    return evaluate(b, rank_pool(b, max_candidates), RING, RUN, HASH)


def label(r: Result) -> str:
    return f"{r.spec.operation_type} {','.join(r.spec.targets)}"
