"""One-to-one ring matching (SRS §28.7): Jaccard ≥ 0.5, maximum Jaccard first; ties by descending similarity,
then ascending reference ring ID, then ascending analytical ring ID."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

THRESHOLD = Fraction(1, 2)


@dataclass(frozen=True)
class Match:
    analytical_id: str
    reference_id: str
    jaccard: Fraction


def jaccard(a: frozenset[str], b: frozenset[str]) -> Fraction:
    union = len(a | b)
    return Fraction(len(a & b), union) if union else Fraction(0)


def match(analytical: dict[str, frozenset[str]], reference: dict[str, frozenset[str]]) -> list[Match]:
    pairs = [
        Match(a_id, r_id, j)
        for a_id, a in analytical.items()
        for r_id, r in reference.items()
        if (j := jaccard(a, r)) >= THRESHOLD
    ]
    pairs.sort(key=lambda m: (-m.jaccard, m.reference_id, m.analytical_id))
    used_a: set[str] = set()
    used_r: set[str] = set()
    out: list[Match] = []
    for m in pairs:
        if m.analytical_id in used_a or m.reference_id in used_r:
            continue
        used_a.add(m.analytical_id)
        used_r.add(m.reference_id)
        out.append(m)
    return out
