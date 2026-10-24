"""One scenario's computation (SRS §16A.2): pool or validated target → residual → metrics → score → rank.
Pure: no database, no graph store, and no analytics, ML, SHAP or scoring code (§16A.7)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from mulenetx.core import ids
from mulenetx.interventions import metrics as metrics_module
from mulenetx.interventions import ranking
from mulenetx.interventions.baseline import Baseline
from mulenetx.interventions.pool import Spec
from mulenetx.interventions.residual import residual


@dataclass
class Result:
    candidate_id: str
    spec: Spec
    metrics: metrics_module.Metrics
    intervention_score: Decimal
    rank_position: int
    affected_account_ids: list[str]
    affected_path_ids: list[str]
    alternative_path_ids: list[str]
    evidence: dict[str, Any]


def evaluate(
    b: Baseline, specs: list[Spec], ring_id: uuid.UUID | str, scoring_run_id: uuid.UUID | str, config_hash: str
) -> list[Result]:
    scored: list[tuple[tuple[Any, ...], Result]] = []
    for spec in specs:
        r = residual(b, spec)
        m = metrics_module.compute(b, spec, r)
        s = ranking.score(m)
        cid = str(
            ids.intervention_candidate_id(
                b.snapshot_id, scoring_run_id, ring_id, spec.operation_type, spec.targets, config_hash
            )
        )
        removed_txs: dict[str, Decimal] = {}
        for p in r.affected:
            removed_txs.update(p.suspicious_txs)
        for p in r.residual:
            for t in p.suspicious_txs:
                removed_txs.pop(t, None)
        evidence = {
            "ranking_inputs": {name: format(getattr(m, name), "f") for name in ranking.WEIGHTS},
            "weights": ranking.WEIGHTS,
            "removed_suspicious_transaction_ids": sorted(removed_txs),
            "baseline_truncated": b.truncated,
            "hypothetical": True,
        }
        result = Result(
            candidate_id=cid,
            spec=spec,
            metrics=m,
            intervention_score=s,
            rank_position=0,
            affected_account_ids=r.affected_accounts,
            affected_path_ids=sorted(p.path_id for p in r.affected),
            alternative_path_ids=sorted(p.path_id for p in r.alternative),
            evidence=evidence,
        )
        scored.append((ranking.sort_key(s, m, cid), result))
    scored.sort(key=lambda x: x[0])
    for position, (_key, result) in enumerate(scored, start=1):
        result.rank_position = position
    return [r for _k, r in scored]
