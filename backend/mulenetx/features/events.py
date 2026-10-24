"""Per-account event history used by the feature formulas (SRS §10, §15)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Event:
    """One transaction seen from one account. A self-transfer is both incoming and outgoing."""

    ts: int  # event time, epoch seconds UTC
    tx_id: str
    amount: float
    tx_type: str
    incoming: bool
    outgoing: bool
    counterparty: str


def in_window(events: list[Event], cutoff: int, window: int) -> list[Event]:
    """Events with cutoff − window < ts ≤ cutoff (half-open window, §10.1)."""
    lo = cutoff - window
    return [e for e in events if lo < e.ts <= cutoff]


def up_to(events: list[Event], cutoff: int) -> list[Event]:
    return [e for e in events if e.ts <= cutoff]
