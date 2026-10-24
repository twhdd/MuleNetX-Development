"""AT-SEC-01: an unauthenticated request to any protected endpoint returns 401 and no protected data."""

import re

import pytest

from tests.endpoints import ENDPOINTS, PLACEHOLDER

pytestmark = pytest.mark.integration

PARAM = re.compile(r"\{[a-z_]+\}")


def _shape(path: str) -> str:
    return PARAM.sub("{}", path)


def _protected_routes(app):
    out = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/v1") or path == "/api/v1/auth/login":
            continue
        for method in sorted(getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}):
            out.append((method, path))
    return out


def test_AT_SEC_01_every_protected_route_requires_auth(app, client) -> None:
    routes = _protected_routes(app)
    assert routes, "no protected routes registered"
    for method, path in routes:
        url = PARAM.sub(PLACEHOLDER, path)
        for headers in ({}, {"Authorization": "Bearer not-a-real-token"}, {"Authorization": "Basic abc"}):
            resp = client.request(method, url, headers=headers, json={})
            assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}"
            assert set(resp.json()) == {"error"}
            assert resp.json()["error"]["code"] == "UNAUTHENTICATED"


def test_AT_SEC_01_registry_covers_routes(app) -> None:
    registered = {(e.method, _shape(e.path)) for e in ENDPOINTS}
    for method, path in _protected_routes(app):
        assert (method, _shape(path)) in registered, f"{method} {path} missing from tests/endpoints.py"
