"""Candidate pool (RANK) and target validation (EVALUATE), SRS §16A.4. No combinations are ever enumerated."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.interventions.baseline import Baseline, Edge, edge_id

ACCOUNT_REMOVAL = "ACCOUNT_REMOVAL"
INTERMEDIARY_REMOVAL = "INTERMEDIARY_REMOVAL"
ACCOUNT_SET_REMOVAL = "ACCOUNT_SET_REMOVAL"
EDGE_REMOVAL = "EDGE_REMOVAL"
OPERATION_TYPES = (ACCOUNT_REMOVAL, INTERMEDIARY_REMOVAL, ACCOUNT_SET_REMOVAL, EDGE_REMOVAL)
K_MAX = 3


@dataclass(frozen=True)
class Spec:
    operation_type: str
    targets: tuple[str, ...]  # sorted account IDs, or (edge_id,)

    @property
    def accounts(self) -> frozenset[str]:
        return frozenset() if self.operation_type == EDGE_REMOVAL else frozenset(self.targets)

    @property
    def edges(self) -> frozenset[Edge]:
        if self.operation_type != EDGE_REMOVAL:
            return frozenset()
        u, v = self.targets[0].split(">", 1)
        return frozenset({(u, v)})


class PoolTooLargeError(Exception):
    """RANK pool above `intervention_max_candidates`: the scenario fails with LIMIT_EXCEEDED (§16A.4.1)."""


def eligibility(b: Baseline) -> tuple[dict[str, str], set[Edge], Counter[str]]:
    """Account → operation type, eligible edges, and paths-per-account counts over P."""
    on_paths: Counter[str] = Counter()
    intermediary: set[str] = set()
    edges: set[Edge] = set()
    for p in b.paths:
        on_paths.update(set(p.accounts))
        intermediary.update(p.accounts[1:-1])
        edges.update(p.edges)
    types = {a: INTERMEDIARY_REMOVAL if a in intermediary else ACCOUNT_REMOVAL for a in on_paths}
    return types, edges, on_paths


def _account_order(b: Baseline, counts: Counter[str], account: str) -> tuple[object, ...]:
    return (-b.score(account), -counts[account], account)


def rank_pool(b: Baseline, max_candidates: int) -> list[Spec]:
    """Every eligible single-account and single-edge candidate in the §16A.4.3 enumeration order."""
    types, edges, counts = eligibility(b)
    if len(types) + len(edges) > max_candidates:
        raise PoolTooLargeError(f"candidate pool {len(types) + len(edges)} exceeds {max_candidates}")
    specs: list[Spec] = []
    for op in (ACCOUNT_REMOVAL, INTERMEDIARY_REMOVAL):
        accounts = sorted((a for a, t in types.items() if t == op), key=lambda a: _account_order(b, counts, a))
        specs += [Spec(op, (a,)) for a in accounts]
    specs += [Spec(EDGE_REMOVAL, (edge_id(e),)) for e in sorted(edges)]
    return specs


def _invalid(reason: str, **details: object) -> AppError:
    return AppError(ec.INTERVENTION_TARGET_INVALID, reason, dict(details))


def validate(b: Baseline, operation_type: str | None, targets: list[str] | None) -> Spec:
    """EVALUATE: exactly one candidate, or 400 INTERVENTION_TARGET_INVALID before any scenario exists."""
    if operation_type not in OPERATION_TYPES:
        raise _invalid("Unknown intervention type.", field="intervention_type")
    if not targets:
        raise _invalid("No target was given.", field="target_ids")
    if len(set(targets)) != len(targets):
        raise _invalid("Targets must be distinct.", field="target_ids")
    types, edges, _counts = eligibility(b)
    if operation_type == EDGE_REMOVAL:
        if len(targets) != 1 or ">" not in targets[0]:
            raise _invalid("EDGE_REMOVAL takes exactly one edge_id of the form source>destination.", field="target_ids")
        u, v = targets[0].split(">", 1)
        if (u, v) not in edges:
            raise _invalid("The edge is not used by any baseline qualifying path.", field="target_ids")
        return Spec(EDGE_REMOVAL, (targets[0],))
    if operation_type == ACCOUNT_SET_REMOVAL:
        if len(targets) > K_MAX:
            raise _invalid(f"At most {K_MAX} accounts may be removed.", field="target_ids", k_max=K_MAX)
        bad = [a for a in targets if a not in types]
        if bad:
            raise _invalid("Every account must lie on a baseline qualifying path.", field="target_ids", ineligible=bad)
        return Spec(ACCOUNT_SET_REMOVAL, tuple(sorted(targets)))
    if len(targets) != 1:
        raise _invalid(f"{operation_type} takes exactly one account.", field="target_ids")
    if types.get(targets[0]) != operation_type:
        raise _invalid(
            f"The account is not eligible for {operation_type}.",
            field="target_ids",
            eligible_type=types.get(targets[0]),
        )
    return Spec(operation_type, (targets[0],))
