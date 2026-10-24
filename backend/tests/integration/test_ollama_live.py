"""Live copilot round trip against a real Ollama (the Compose `ollama` service, model pulled by `ollama-pull`).

Marked `ollama`; `make test` deselects it. Run with the service reachable at OLLAMA_LIVE_URL
(default http://127.0.0.1:11434) and OLLAMA_LIVE_MODEL pulled. OLLAMA_LIVE_NUM_CTX overrides the model window on
hosts without memory for the full one (the default is the service's: context + output budget + 2,048):

    uv run pytest tests/integration/test_ollama_live.py -m ollama
"""

import os

import pytest

from mulenetx.api.deps import get_services
from mulenetx.copilot.ollama_client import OllamaClient
from tests.apiutil import _Req
from tests.ingestutil import seed_and_activate

pytestmark = [pytest.mark.integration, pytest.mark.ollama]

URL = os.environ.get("OLLAMA_LIVE_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("OLLAMA_LIVE_MODEL", "qwen2.5:7b-instruct")
NUM_CTX = os.environ.get("OLLAMA_LIVE_NUM_CTX")
# generous: the point is the round trip, not the 20 s production timeout (CPU-only hosts are far slower)
TIMEOUT = float(os.environ.get("OLLAMA_LIVE_TIMEOUT", "600"))


def test_ollama_live_round_trip(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("A", "B", 900.0, 1), ("B", "C", 880.0, 2)], key="live")
    service = get_services(_Req(app)).copilot
    num_ctx = int(NUM_CTX) if NUM_CTX else service.client.num_ctx
    service.client = OllamaClient(URL, MODEL, TIMEOUT, num_ctx=num_ctx)
    analyst = users("ANALYST")
    resp = client.post(
        "/api/v1/copilot/query",
        json={"question": "Why is this account risky?", "account_id": "live:B"},
        headers=analyst.headers,
    )
    # A real model may produce an answer the validator rejects; both outcomes are contract-conformant.
    assert resp.status_code in (200, 503), resp.text
    body = resp.json()
    print("live copilot:", resp.status_code, body.get("error", {}).get("details") or body.get("intent"))  # noqa: T201
    if resp.status_code == 200:
        assert body["label"] == "AI INTERPRETATION" and body["model"]["model"]
        assert all(item["refs"] for item in body["facts"])
    else:
        assert body["error"]["code"] == "AI_RESPONSE_INVALID"
