"""Motif confidence (SRS §15.9.7): a deterministic pattern-strength score in [0, 1], never a risk measure."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
from typing import Any

from mulenetx.core.decimal import round7

# motif type → (required_structure, expected_minimum_participants, configured_window_seconds)
PARAMETERS: dict[str, tuple[int, int, int]] = {
    "RAPID_PASS_THROUGH": (2, 3, 900),
    "FAN_IN": (3, 4, 3600),
    "FAN_OUT": (3, 4, 3600),
    "CIRCULAR_FLOW": (3, 3, 86_400),
    "LAYERED_MOVEMENT": (4, 5, 86_400),
    "BURST_ACTIVITY": (5, 3, 3600),
}


def _clamp(x: Fraction) -> Fraction:
    return max(Fraction(0), min(Fraction(1), x))


def _dec(x: Fraction) -> Decimal:
    return round7(Decimal(x.numerator) / Decimal(x.denominator))


def confidence(
    motif_type: str, observed_structure: int, participants: int, span_seconds: int, gaps: list[int] | None = None
) -> tuple[Decimal, dict[str, Any]]:
    required, expected_participants, window = PARAMETERS[motif_type]
    structural = _clamp(Fraction(observed_structure, required))
    if motif_type == "BURST_ACTIVITY":
        temporal = Fraction(1)
    elif motif_type == "RAPID_PASS_THROUGH":
        assert gaps, "rapid pass-through needs its per-hop gaps"
        temporal = sum((_clamp(1 - Fraction(g, window)) for g in gaps), Fraction(0)) / len(gaps)
    else:
        temporal = _clamp(1 - Fraction(span_seconds, window))
    participant = _clamp(Fraction(participants, expected_participants))
    value = (structural + temporal + participant) / 3
    components = {
        "structural_match": format(_dec(structural), "f"),
        "temporal_match": format(_dec(temporal), "f"),
        "participant_match": format(_dec(participant), "f"),
        "required_structure": required,
        "observed_required_structure": observed_structure,
        "expected_minimum_participants": expected_participants,
        "distinct_participants": participants,
        "configured_window_seconds": window,
        "observed_span_seconds": span_seconds,
    }
    return _dec(_clamp(value)), components
