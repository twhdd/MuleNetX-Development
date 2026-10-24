"""Pipeline state machine (SRS §7.6) as data, and the single `advance` function that enforces it."""

from __future__ import annotations

from typing import Final

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError

STATES: Final[tuple[str, ...]] = (
    "CREATED",
    "INGESTING",
    "INGESTED",
    "PROFILING",
    "PROFILED",
    "GRAPH_BUILDING",
    "GRAPH_READY",
    "ANALYTICS_RUNNING",
    "ANALYTICS_READY",
    "FEATURES_RUNNING",
    "FEATURES_READY",
    "TRAINING",
    "MODEL_READY",
    "SCORING",
    "SCORED",
    "RING_ANALYSIS",
    "READY",
    "FAILED",
)

TERMINAL: Final[frozenset[str]] = frozenset({"READY", "FAILED"})

# Stage running state -> (state before it, state after it).
STAGES: Final[dict[str, tuple[str, str]]] = {
    "INGESTING": ("CREATED", "INGESTED"),
    "PROFILING": ("INGESTED", "PROFILED"),
    "GRAPH_BUILDING": ("PROFILED", "GRAPH_READY"),
    "ANALYTICS_RUNNING": ("GRAPH_READY", "ANALYTICS_READY"),
    "FEATURES_RUNNING": ("ANALYTICS_READY", "FEATURES_READY"),
    "TRAINING": ("FEATURES_READY", "MODEL_READY"),
    "SCORING": ("FEATURES_READY", "SCORED"),  # also entered from MODEL_READY
    "RING_ANALYSIS": ("SCORED", "READY"),  # READY = §6.9 activation, committed with the stage's final outputs
}
RUNNING_STATES: Final[frozenset[str]] = frozenset(STAGES)

# Legal transitions. Every non-terminal state may also go to FAILED (rule 1); FAILED goes back to a
# running stage only through POST /pipeline-runs/{id}/retry (§7.7).
_FORWARD: Final[dict[str, frozenset[str]]] = {
    "CREATED": frozenset({"INGESTING"}),
    "INGESTING": frozenset({"INGESTED"}),
    "INGESTED": frozenset({"PROFILING"}),
    "PROFILING": frozenset({"PROFILED"}),
    "PROFILED": frozenset({"GRAPH_BUILDING"}),
    "GRAPH_BUILDING": frozenset({"GRAPH_READY"}),
    "GRAPH_READY": frozenset({"ANALYTICS_RUNNING"}),
    "ANALYTICS_RUNNING": frozenset({"ANALYTICS_READY"}),
    "ANALYTICS_READY": frozenset({"FEATURES_RUNNING"}),
    "FEATURES_RUNNING": frozenset({"FEATURES_READY"}),
    "FEATURES_READY": frozenset({"TRAINING", "SCORING"}),
    "TRAINING": frozenset({"MODEL_READY"}),
    "MODEL_READY": frozenset({"SCORING"}),
    "SCORING": frozenset({"SCORED"}),
    "SCORED": frozenset({"RING_ANALYSIS"}),
    "RING_ANALYSIS": frozenset({"READY"}),
    "READY": frozenset(),
    "FAILED": RUNNING_STATES,
}

TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    state: targets | (frozenset({"FAILED"}) if state not in TERMINAL else frozenset())
    for state, targets in _FORWARD.items()
}


class InvalidTransitionError(AppError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            ec.CONFLICT, f"Pipeline transition {current} -> {target} is not allowed.", {"from": current, "to": target}
        )
        self.current = current
        self.target = target


def is_legal(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, frozenset())


def advance(current: str, target: str) -> str:
    """Return `target` if `current -> target` is in the table; raise otherwise."""
    if not is_legal(current, target):
        raise InvalidTransitionError(current, target)
    return target


def stage_for_running_state(state: str) -> tuple[str, str]:
    return STAGES[state]
