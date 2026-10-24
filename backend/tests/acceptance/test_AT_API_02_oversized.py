"""AT-API-02: oversized requests are rejected server-side: result/parameter limits with `400 LIMIT_EXCEEDED`,
bodies over the §19.2 limit with `413 PAYLOAD_TOO_LARGE`, both in the §19.3 envelope (SR-17)."""

import pytest

from tests.caseutil import new_case
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration

KB = 1024

LIMIT_CASES = [
    ("/api/v1/users", {"page_size": 101}),
    ("/api/v1/ingestion", {"page_size": 101}),
    ("/api/v1/pipeline-runs", {"page_size": 101}),
    ("/api/v1/models", {"page_size": 101}),
    ("/api/v1/accounts", {"page_size": 101}),
    ("/api/v1/accounts", {"q": "C" * 129}),
    ("/api/v1/accounts/x:CA/transactions", {"page_size": 101}),
    ("/api/v1/accounts/x:CA/risk/history", {"page_size": 101}),
    ("/api/v1/accounts/x:CA/shap", {"top_n": 51}),
    ("/api/v1/accounts/x:CA/community", {"page_size": 101}),
    ("/api/v1/graph/neighborhood", {"account_id": "x:CA", "depth": 4}),
    ("/api/v1/graph/neighborhood", {"account_id": "x:CA", "max_nodes": 1001}),
    ("/api/v1/graph/neighborhood", {"account_id": "x:CA", "max_edges": 5001}),
    ("/api/v1/graph/path", {"source_account_id": "x:CA", "destination_account_id": "x:CB", "max_depth": 6}),
    ("/api/v1/graph/path", {"source_account_id": "x:CA", "destination_account_id": "x:CB", "max_results": 101}),
    ("/api/v1/communities", {"page_size": 101}),
    ("/api/v1/cases", {"page_size": 101}),
    ("/api/v1/audit", {"page_size": 101}),
]


@pytest.mark.parametrize(("url", "params"), LIMIT_CASES, ids=[f"{u}?{list(p)[-1]}" for u, p in LIMIT_CASES])
def test_AT_API_02_limit_exceeded(client, users, url, params) -> None:
    resp = client.get(url, params=params, headers=users("ADMIN").headers)
    assert resp.status_code == 400, resp.text
    body = resp.json()
    assert body["error"]["code"] == "LIMIT_EXCEEDED", body
    assert set(body["error"]) == {"code", "message", "request_id", "details"}


def test_AT_API_02_transaction_range(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("CA", "CB", 1.0, 1)], key="rng")
    params = {"start": "2020-01-01T00:00:00Z", "end": "2020-03-01T00:00:00Z"}  # > max_transaction_range (31 d)
    resp = client.get("/api/v1/accounts/rng:CA/transactions", params=params, headers=admin.headers)
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "LIMIT_EXCEEDED"


def test_AT_API_02_payload_too_large(client, users) -> None:
    admin = users("ADMIN")
    case = new_case(client, admin)
    c = f"/api/v1/cases/{case['case_id']}"
    oversized = [
        ("POST", "/api/v1/auth/login", 4 * KB, {}),
        ("POST", "/api/v1/users", 4 * KB, admin.headers),
        ("PATCH", "/api/v1/users/00000000-0000-4000-8000-000000000000", 4 * KB, admin.headers),
        ("POST", "/api/v1/cases", 16 * KB, admin.headers),
        ("PATCH", c, 16 * KB, admin.headers),
        ("POST", f"{c}/findings", 64 * KB, admin.headers),
        ("POST", f"{c}/subjects", 64 * KB, admin.headers),  # agent default for routes without an SRS limit
    ]
    for method, url, limit, headers in oversized:
        payload = b'{"pad": "' + b"x" * limit + b'"}'
        resp = client.request(method, url, content=payload, headers={**headers, "Content-Type": "application/json"})
        assert resp.status_code == 413, (method, url, resp.status_code)
        body = resp.json()
        assert body["error"]["code"] == "PAYLOAD_TOO_LARGE" and body["error"]["details"] == {"limit": limit}
        assert body["error"]["request_id"] == resp.headers["x-request-id"]
    just_under = b'{"title": "' + b"t" * 200 + b'", "priority": "LOW", "pad": "' + b"x" * (15 * KB) + b'"}'
    resp = client.post(
        "/api/v1/cases", content=just_under, headers={**admin.headers, "Content-Type": "application/json"}
    )
    assert resp.status_code == 400  # within the body limit: reaches validation (unknown field) instead of 413
