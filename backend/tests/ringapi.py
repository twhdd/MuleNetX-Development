"""Shared setup for ring API tests: the synthetic dataset yields both candidate classes."""

from __future__ import annotations

from typing import Any

from tests.ingestutil import seed_synth_and_activate


def rings_by_class(app: Any, client: Any, admin: Any, key: str) -> dict[str, dict[str, Any]]:
    seed_synth_and_activate(app, client, admin, key=key)
    items = client.get("/api/v1/rings", params={"page_size": 100}, headers=admin.headers).json()["items"]
    found: dict[str, dict[str, Any]] = {}
    for r in items:
        found.setdefault(r["candidate_class"], r)
    assert set(found) == {"SUSPICIOUS_COMMUNITY", "POTENTIAL_FRAUD_RING_CANDIDATE"}, items
    return found
