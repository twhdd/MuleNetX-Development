"""Case state machine (SRS §17.2) as data."""

from __future__ import annotations

from typing import Final

STATUSES: Final[tuple[str, ...]] = ("OPEN", "IN_REVIEW", "ESCALATED", "RESOLVED", "FALSE_POSITIVE", "CLOSED")
PRIORITIES: Final[tuple[str, ...]] = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "OPEN": frozenset({"IN_REVIEW"}),
    "IN_REVIEW": frozenset({"ESCALATED", "RESOLVED", "FALSE_POSITIVE"}),
    "ESCALATED": frozenset({"IN_REVIEW", "RESOLVED", "FALSE_POSITIVE"}),
    "RESOLVED": frozenset({"CLOSED"}),
    "FALSE_POSITIVE": frozenset({"CLOSED"}),
    "CLOSED": frozenset(),
}


def is_valid_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, frozenset())
