"""Disruption, risk-reduction and cost metrics (SRS §16A.9–§16A.13) with explicit zero-denominator rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_EVEN, Decimal

from mulenetx.core.decimal import round7
from mulenetx.interventions.baseline import Baseline, flow, risk_mass
from mulenetx.interventions.pool import ACCOUNT_SET_REMOVAL, K_MAX, Spec
from mulenetx.interventions.residual import Residual

ZERO = Decimal(0)
ONE = Decimal(1)


def money4(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)


def _clamp(x: Decimal) -> Decimal:
    return min(ONE, max(ZERO, x))


@dataclass
class Metrics:
    residual_suspicious_flow: Decimal
    flow_disruption: Decimal
    flow_disruption_percentage: Decimal
    residual_suspicious_paths: int
    normalized_path_disruption: Decimal
    residual_reachable_suspicious_pairs: int
    normalized_connectivity_disruption: Decimal
    residual_risk_mass: Decimal
    residual_network_risk: Decimal
    normalized_risk_reduction: Decimal
    intervention_cost: Decimal
    normalized_intervention_cost: Decimal
    unavailable: list[str] = field(default_factory=list)


def compute(b: Baseline, spec: Spec, r: Residual) -> Metrics:
    unavailable: list[str] = []
    residual_flow = flow(r.residual)
    disruption = b.suspicious_flow - residual_flow
    if b.suspicious_flow == 0:
        disruption, flow_pct = ZERO, ZERO
        unavailable.append("flow_disruption")
    else:
        flow_pct = round7(_clamp(disruption / b.suspicious_flow))

    n_base, n_res = len(b.paths), len(r.residual)
    if n_base == 0:
        path_d = ZERO
        unavailable.append("path_disruption")
    else:
        path_d = round7(Decimal(n_base - n_res) / n_base)

    res_pairs = {p.pair for p in r.residual}
    if not b.pairs:
        conn_d = ZERO
        unavailable.append("connectivity_disruption")
    else:
        conn_d = round7(Decimal(len(b.pairs) - len(res_pairs)) / len(b.pairs))

    res_mass = risk_mass(r.residual, b.run, spec.accounts)
    if b.risk_mass == 0:
        res_risk, reduction = ZERO, ZERO
        unavailable.append("risk_reduction")
    else:
        res_risk = round7(_clamp(res_mass / b.risk_mass))
        reduction = round7(_clamp(ONE - res_mass / b.risk_mass))

    cost = Decimal(len(spec.targets)) if spec.operation_type == ACCOUNT_SET_REMOVAL else ONE
    return Metrics(
        residual_suspicious_flow=residual_flow,
        flow_disruption=disruption,
        flow_disruption_percentage=flow_pct,
        residual_suspicious_paths=n_res,
        normalized_path_disruption=path_d,
        residual_reachable_suspicious_pairs=len(res_pairs),
        normalized_connectivity_disruption=conn_d,
        residual_risk_mass=res_mass,
        residual_network_risk=res_risk,
        normalized_risk_reduction=reduction,
        intervention_cost=cost,
        normalized_intervention_cost=round7(_clamp(cost / K_MAX)),
        unavailable=unavailable,
    )
