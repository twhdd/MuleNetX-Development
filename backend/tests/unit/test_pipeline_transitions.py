"""Pipeline transition table (SRS §7.6, §27.1): every legal transition accepted, every other pair rejected."""

import itertools

import pytest

from mulenetx.jobs.pipeline_state import STATES, InvalidTransitionError, advance, is_legal

CHAIN = [
    ("CREATED", "INGESTING"),
    ("INGESTING", "INGESTED"),
    ("INGESTED", "PROFILING"),
    ("PROFILING", "PROFILED"),
    ("PROFILED", "GRAPH_BUILDING"),
    ("GRAPH_BUILDING", "GRAPH_READY"),
    ("GRAPH_READY", "ANALYTICS_RUNNING"),
    ("ANALYTICS_RUNNING", "ANALYTICS_READY"),
    ("ANALYTICS_READY", "FEATURES_RUNNING"),
    ("FEATURES_RUNNING", "FEATURES_READY"),
    ("FEATURES_READY", "TRAINING"),
    ("FEATURES_READY", "SCORING"),
    ("TRAINING", "MODEL_READY"),
    ("MODEL_READY", "SCORING"),
    ("SCORING", "SCORED"),
    ("SCORED", "RING_ANALYSIS"),
    ("RING_ANALYSIS", "READY"),
]
ACTIVE = [s for s in STATES if s not in ("READY", "FAILED")]
RESUMABLE = [
    "INGESTING",
    "PROFILING",
    "GRAPH_BUILDING",
    "ANALYTICS_RUNNING",
    "FEATURES_RUNNING",
    "TRAINING",
    "SCORING",
    "RING_ANALYSIS",
]
LEGAL = set(CHAIN) | {(s, "FAILED") for s in ACTIVE} | {("FAILED", s) for s in RESUMABLE}


def test_state_set() -> None:
    assert len(STATES) == 18


@pytest.mark.parametrize(("current", "target"), sorted(LEGAL))
def test_legal_transition_accepted(current: str, target: str) -> None:
    assert advance(current, target) == target


def test_every_other_pair_rejected() -> None:
    rejected = 0
    for current, target in itertools.product(STATES, STATES):
        if (current, target) in LEGAL:
            continue
        assert not is_legal(current, target)
        with pytest.raises(InvalidTransitionError):
            advance(current, target)
        rejected += 1
    assert rejected == 18 * 18 - len(LEGAL)


def test_ready_is_terminal() -> None:
    assert all(not is_legal("READY", s) for s in STATES)
