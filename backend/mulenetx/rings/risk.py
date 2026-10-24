"""Ring risk (SRS §9A.3): separate from account risk; unavailable components contribute 0, no renormalization."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from mulenetx.core.decimal import round7
from mulenetx.motifs.common import MOTIF_TYPES
from mulenetx.rings.candidates import ratio
from mulenetx.rings.features import RingFeatures
from mulenetx.rings.inputs import ContextInputs
from mulenetx.rings.membership import Membership
from mulenetx.risk.tiers import tier

WEIGHTS = {
    "member_risk": Decimal("0.25"),
    "transaction_risk": Decimal("0.20"),
    "topology_signal": Decimal("0.20"),
    "temporal_signal": Decimal("0.20"),
    "money_flow_signal": Decimal("0.15"),
}


@dataclass(frozen=True)
class RingRisk:
    components: dict[str, Decimal]
    availability: dict[str, str]
    score: Decimal
    tier: str
    temporal_indicators: dict[str, int]


def compute(ctx: ContextInputs, m: Membership, f: RingFeatures) -> RingRisk:
    members = set(m.members)
    assessed = [ctx.run.final_scores[a] for a in m.members if a in ctx.run.final_scores]
    if assessed:
        member_risk, member_ok = round7(sum(assessed, Decimal(0)) / len(assessed)), True
    else:
        member_risk, member_ok = Decimal(0), False
    topology = round7(sum((f.values[k] for k in ("CS", "FI", "FO", "CP", "SPD")), Decimal(0)) / 5)
    indicators = {t: int(any(x.motif_type == t and x.accounts <= members for x in ctx.motifs)) for t in MOTIF_TYPES}
    temporal = round7(Decimal(sum(indicators.values())) / len(MOTIF_TYPES))
    money, money_ok = ratio(f.scope.suspicious_flow, f.scope.eligible_flow)
    components = {
        "member_risk": member_risk,
        "transaction_risk": f.values["RSD"],
        "topology_signal": topology,
        "temporal_signal": temporal,
        "money_flow_signal": money,
    }
    availability = {
        "member_risk": "AVAILABLE" if member_ok else "UNAVAILABLE",
        "transaction_risk": "AVAILABLE" if f.availability["RSD"] == "AVAILABLE" else "UNAVAILABLE",
        "topology_signal": "AVAILABLE",
        "temporal_signal": "AVAILABLE",
        "money_flow_signal": "AVAILABLE" if money_ok else "UNAVAILABLE",
    }
    if f.paths_truncated and money_ok:
        availability["money_flow_signal"] = "LOWER_BOUND_TRUNCATED"
    raw = sum((WEIGHTS[k] * v for k, v in components.items()), Decimal(0))
    score = round7(min(Decimal(1), max(Decimal(0), raw)))
    return RingRisk(components, availability, score, tier(score, ctx.tier_thresholds), indicators)
