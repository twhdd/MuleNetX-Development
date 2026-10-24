"""Case test helpers."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from tests.apiutil import Actor


def new_case(client: TestClient, actor: Actor, **extra: Any) -> dict[str, Any]:
    resp = client.post(
        "/api/v1/cases", json={"title": "Possible mule network", "priority": "HIGH", **extra}, headers=actor.headers
    )
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body


def patch(client: TestClient, actor: Actor, case: dict[str, Any], **changes: Any) -> Any:
    return client.patch(
        f"/api/v1/cases/{case['case_id']}", json={"version": case["version"], **changes}, headers=actor.headers
    )
