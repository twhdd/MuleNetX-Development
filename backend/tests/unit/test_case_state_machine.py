"""Case state machine (SRS §17.2): every legal transition accepted, every other pair rejected."""

import itertools

from mulenetx.investigation.cases import STATUSES, TRANSITIONS, is_valid_transition

LEGAL = {
    ("OPEN", "IN_REVIEW"),
    ("IN_REVIEW", "ESCALATED"),
    ("IN_REVIEW", "RESOLVED"),
    ("IN_REVIEW", "FALSE_POSITIVE"),
    ("ESCALATED", "IN_REVIEW"),
    ("ESCALATED", "RESOLVED"),
    ("ESCALATED", "FALSE_POSITIVE"),
    ("RESOLVED", "CLOSED"),
    ("FALSE_POSITIVE", "CLOSED"),
}


def test_transitions_exact() -> None:
    for a, b in itertools.product(STATUSES, STATUSES):
        assert is_valid_transition(a, b) == ((a, b) in LEGAL), (a, b)
    assert TRANSITIONS["CLOSED"] == frozenset()
