"""Run intervention scenarios end to end against the synthetic dataset."""

from __future__ import annotations

from typing import Any

from tests.ingestutil import run_worker
from tests.ringapi import rings_by_class


def potential_ring(app: Any, client: Any, admin: Any, key: str) -> dict[str, Any]:
    return rings_by_class(app, client, admin, key)["POTENTIAL_FRAUD_RING_CANDIDATE"]


def simulate(client: Any, actor: Any, ring_id: str, body: dict[str, Any]) -> Any:
    return client.post(f"/api/v1/rings/{ring_id}/interventions/simulate", json=body, headers=actor.headers)


def complete(app: Any, client: Any, actor: Any, scenario_id: str) -> dict[str, Any]:
    run_worker(app, timeout=600)
    scenario: dict[str, Any] = client.get(f"/api/v1/interventions/{scenario_id}", headers=actor.headers).json()
    return scenario
