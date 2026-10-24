"""Error envelope (SRS §19.3) and request ID (§19.1)."""

import uuid

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError, limit_exceeded
from mulenetx.main import create_app
from tests.conftest import make_settings


class Body(BaseModel):
    name: str


def _app() -> FastAPI:
    app = create_app(make_settings())
    router = APIRouter()

    @router.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret detail /etc/passwd SELECT * FROM users")

    @router.get("/limit")
    def limit() -> None:
        raise limit_exceeded("depth", 3)

    @router.post("/echo")
    def echo(body: Body) -> dict[str, str]:
        return {"name": body.name}

    app.include_router(router)
    return app


def test_app_error_envelope() -> None:
    client = TestClient(_app())
    resp = client.get("/limit")
    assert resp.status_code == 400
    body = resp.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id", "details"}
    assert body["error"]["code"] == "LIMIT_EXCEEDED"
    assert body["error"]["details"] == {"field": "depth", "limit": 3}
    assert body["error"]["request_id"] == resp.headers["x-request-id"]


def test_unknown_exception_is_generic_500_without_stack_trace() -> None:
    client = TestClient(_app(), raise_server_exceptions=False)
    resp = client.get("/boom")
    assert resp.status_code == 500
    text = resp.text
    assert "Traceback" not in text and "SELECT" not in text and "/etc/passwd" not in text
    assert resp.json()["error"]["code"] == "INTERNAL"


def test_valid_request_id_echoed_invalid_replaced() -> None:
    client = TestClient(_app())
    rid = str(uuid.uuid4())
    assert client.get("/limit", headers={"X-Request-ID": rid}).headers["x-request-id"] == rid
    replaced = client.get("/limit", headers={"X-Request-ID": "not-a-uuid"}).headers["x-request-id"]
    assert replaced != "not-a-uuid"
    uuid.UUID(replaced)


def test_validation_error_lists_fields_only() -> None:
    client = TestClient(_app())
    resp = client.post("/echo", json={"name": 5, "x": "<script>"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
    assert resp.json()["error"]["details"] == {"fields": ["name"]}
    assert "<script>" not in resp.text


def test_unknown_route_404_envelope() -> None:
    resp = TestClient(_app()).get("/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_body_limit_413() -> None:
    client = TestClient(_app())
    resp = client.post("/echo", content=b"x" * (65 * 1024), headers={"content-type": "application/json"})
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_every_error_code_has_spec() -> None:
    assert ec.ERRORS[ec.GRAPH_UNAVAILABLE].http_status == 503
    assert AppError(ec.SNAPSHOT_RETIRED).http_status == 410
    assert len(ec.ERRORS) == 32
