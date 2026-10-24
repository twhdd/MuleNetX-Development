"""Deterministic composition (SRS §12.1, §12.4, §12.8) in decimal arithmetic, rounded half-even to 7 dp.

pre_propagation_score = w_ml·ml + w_g·g + w_b·b + w_r·r   (unavailable components contribute 0)
final_score           = clamp(pre_propagation_score + w_p·propagated_risk, 0, 1)
Component scores enter as their rounded (stored) values, so every stored score is reproducible from the
stored components.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from mulenetx.core.decimal import ONE, ZERO, D, clamp, round7
from mulenetx.risk.tiers import tier


@dataclass(frozen=True)
class Weights:
    ml: Decimal
    graph: Decimal
    behavioral: Decimal
    propagation: Decimal
    rules: Decimal

    @classmethod
    def from_config(cls, weights: Mapping[str, str]) -> Weights:
        return cls(
            D(weights["ml"]),
            D(weights["graph"]),
            D(weights["behavioral"]),
            D(weights["propagation"]),
            D(weights["rules"]),
        )


@dataclass(frozen=True)
class Components:
    ml_score: Decimal | None  # None when the ML component is unavailable
    graph: Decimal
    graph_available: bool
    behavioral: Decimal
    behavioral_available: bool
    rules: Decimal
    rules_available: bool = True


@dataclass(frozen=True)
class Composition:
    pre_propagation_score: Decimal
    propagated_risk: Decimal
    final_score: Decimal
    risk_tier: str
    signal_coverage: Decimal
    max_attainable_score: Decimal


def pre_propagation(c: Components, w: Weights) -> Decimal:
    ml = ZERO if c.ml_score is None else round7(c.ml_score)
    total = w.ml * ml + w.graph * round7(c.graph) + w.behavioral * round7(c.behavioral) + w.rules * round7(c.rules)
    return round7(clamp(total))


def final(pre: Decimal, propagated: Decimal, w: Weights) -> Decimal:
    return round7(clamp(round7(pre) + w.propagation * round7(propagated)))


def coverage(c: Components, w: Weights) -> Decimal:
    """Weight share of the available components (propagation is always available)."""
    share = w.propagation
    share += w.ml if c.ml_score is not None else ZERO
    share += w.graph if c.graph_available else ZERO
    share += w.behavioral if c.behavioral_available else ZERO
    share += w.rules if c.rules_available else ZERO
    return round7(share)


def max_attainable(c: Components, propagated: Decimal, w: Weights) -> Decimal:
    """The score the account would have with every unavailable component at 1 (§12.8)."""
    lifted = Components(
        ml_score=ONE if c.ml_score is None else c.ml_score,
        graph=c.graph if c.graph_available else ONE,
        graph_available=True,
        behavioral=c.behavioral if c.behavioral_available else ONE,
        behavioral_available=True,
        rules=c.rules if c.rules_available else ONE,
        rules_available=True,
    )
    return final(pre_propagation(lifted, w), propagated, w)


def compose(c: Components, propagated: Decimal, w: Weights, thresholds: Mapping[str, str]) -> Composition:
    pre = pre_propagation(c, w)
    fin = final(pre, propagated, w)
    return Composition(
        pre, round7(propagated), fin, tier(fin, thresholds), coverage(c, w), max_attainable(c, propagated, w)
    )
