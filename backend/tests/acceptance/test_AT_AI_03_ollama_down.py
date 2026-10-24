"""AT-AI-03: with Ollama unavailable the copilot returns 503 COPILOT_UNAVAILABLE and investigation stays usable."""

import httpx
import pytest

from tests.apiutil import audit_events
from tests.copilotutil import install
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration

URL = "/api/v1/copilot/query"


def refuse(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("connection refused", request=request)


def slow(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("timed out", request=request)


def broken(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="model crashed")


@pytest.mark.parametrize("handler", [refuse, slow, broken], ids=["down", "timeout", "server-error"])
def test_AT_AI_03_ollama_down(app, client, users, handler) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("A", "B", 75.0, 1)], key="ai3")
    install(app, transport=httpx.MockTransport(handler))
    analyst = users("ANALYST")
    resp = client.post(URL, json={"question": "Why is the risk high?", "account_id": "ai3:A"}, headers=analyst.headers)
    assert resp.status_code == 503, resp.text
    assert resp.json()["error"]["code"] == "COPILOT_UNAVAILABLE"
    # the rest of the investigation works
    assert client.get("/api/v1/accounts/ai3:A", headers=analyst.headers).status_code == 200
    assert client.get("/api/v1/accounts/ai3:A/transactions", headers=analyst.headers).status_code == 200
    assert (
        client.post("/api/v1/cases", json={"title": "t", "priority": "LOW"}, headers=analyst.headers).status_code == 201
    )
    event = audit_events(app, action="copilot.query")[-1]
    assert event.outcome == "FAILED" and event.metadata_["error_code"] == "COPILOT_UNAVAILABLE"


def test_AT_AI_03_unreachable_host(app, client, users) -> None:
    """No mock: a real connection to a closed local port."""
    from mulenetx.api.deps import get_services
    from mulenetx.copilot.ollama_client import OllamaClient
    from tests.apiutil import _Req

    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("A", "B", 75.0, 1)], key="ai3b")
    get_services(_Req(app)).copilot.client = OllamaClient("http://127.0.0.1:9", "qwen-test", 2.0)
    analyst = users("ANALYST")
    resp = client.post(URL, json={"question": "summary", "account_id": "ai3b:A"}, headers=analyst.headers)
    assert resp.status_code == 503 and resp.json()["error"]["code"] == "COPILOT_UNAVAILABLE"
