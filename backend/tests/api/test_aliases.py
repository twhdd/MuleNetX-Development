"""Compatibility aliases (SRS §19.2.1): same response as the target plus Deprecation and Link headers."""

import pytest

from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration


def test_money_flow_alias(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("CA", "CB", 1.0, 1), ("CB", "CC", 2.0, 2)], key="al")
    params = {"source_account_id": "al:CA", "destination_account_id": "al:CC"}
    target = client.get("/api/v1/graph/path", params=params, headers=admin.headers)
    alias = client.get("/api/v1/money-flow", params=params, headers=admin.headers)
    assert alias.status_code == 200
    assert alias.headers["deprecation"] == "true" and "/api/v1/graph/path" in alias.headers["link"]
    strip = lambda b: {k: v for k, v in b.items() if k != "computed_at"}  # noqa: E731
    assert strip(alias.json()) == strip(target.json())
    analyst = users("ANALYST")
    assert client.get("/api/v1/money-flow", params=params, headers=analyst.headers).status_code == 200
