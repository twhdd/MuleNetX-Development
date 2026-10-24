"""Helpers for feature tests."""

from __future__ import annotations

import itertools

from mulenetx.features.events import Event

H = 3600
_ids = itertools.count(1)


def ev(
    hours: float, amount: float, direction: str, cp: str, tx_type: str = "TRANSFER", tx_id: str | None = None
) -> Event:
    return Event(
        ts=int(hours * H),
        tx_id=tx_id or f"t{next(_ids):06d}",
        amount=amount,
        tx_type=tx_type,
        incoming=direction in ("in", "self"),
        outgoing=direction in ("out", "self"),
        counterparty=cp,
    )


def sort(events: list[Event]) -> list[Event]:
    return sorted(events, key=lambda e: (e.ts, e.tx_id))
