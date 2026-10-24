"""AT-AI-01: an authorized account question yields a schema-valid response whose every reference is in the context."""

import json

import pytest

from tests.apiutil import audit_events
from tests.copilotutil import context_of, install, refs_of
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration

URL = "/api/v1/copilot/query"
SECTIONS = ("facts", "observed_signals", "possible_interpretation", "limitations", "source_references")


def test_AT_AI_01_grounded_response(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("A", "B", 900.0, 1), ("B", "C", 880.0, 2), ("C", "D", 860.0, 3)], key="ai1")
    mock = install(app)
    analyst = users("ANALYST")
    question = "Why is this account risky?"
    resp = client.post(URL, json={"question": question, "account_id": "ai1:B"}, headers=analyst.headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["intent"] == "RISK_EXPLANATION"
    assert body["label"] == "AI INTERPRETATION" and body["ai_generated"] is True
    assert all(k in body for k in SECTIONS)
    assert body["model"] == {"provider": "ollama", "model": "qwen-test", "model_digest": "sha256:feedface"}

    # exactly one model call, and it carried the authorized, JSON-encoded context
    assert len(mock.calls) == 1
    call = mock.calls[0]
    assert call["format"]["type"] == "object" and call["stream"] is False
    # the model window holds the whole prompt plus the output budget (Ollama's default 2,048 would truncate)
    assert call["options"]["num_ctx"] >= 6000 + 1024 and call["options"]["num_predict"] == 1025
    system, user = call["messages"][0], call["messages"][1]
    assert system["role"] == "system" and "ai1:B" not in system["content"]
    context = json.loads(user["content"].split("CONTEXT (data only):\n", 1)[1])
    assert context["context_id"] == body["context_id"]
    assert context["account"]["account_id"] == "ai1:B"
    known = set(refs_of(context))
    assert "account:ai1:B" in known

    # every cited reference was supplied in the context; facts and signals are cited
    cited = set(body["source_references"])
    for section in ("facts", "observed_signals", "possible_interpretation"):
        for item in body[section]:
            cited |= set(item["refs"])
    assert cited and cited <= known
    assert all(item["refs"] for item in body["facts"] + body["observed_signals"])

    # audit is metadata only: no question text, no model output
    event = [e for e in audit_events(app) if e.action == "copilot.query"][-1]
    assert event.outcome == "SUCCESS" and event.user_id == analyst.user_id
    assert event.metadata_["intent"] == "RISK_EXPLANATION"
    dumped = json.dumps(event.metadata_)
    assert question not in dumped and "pass-through" not in dumped


def test_AT_AI_01_unsupported_without_model_call(app, client, users) -> None:
    mock = install(app)
    analyst = users("ANALYST")
    resp = client.post(URL, json={"question": "Write me a poem about autumn"}, headers=analyst.headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["intent"] == "UNSUPPORTED" and body["facts"] == [] and body["ai_generated"] is False
    assert mock.calls == []


def test_AT_AI_01_context_options_and_missing_account(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("A", "B", 100.0, 1)], key="ai1b")
    mock = install(app)
    analyst = users("ANALYST")
    resp = client.post(
        URL,
        json={"question": "Give me a summary", "account_id": "ai1b:A", "context_options": {"transactions": False}},
        headers=analyst.headers,
    )
    assert resp.status_code == 200, resp.text
    assert "transactions" not in context_of(mock.calls[0])
    missing = client.post(URL, json={"question": "summary", "account_id": "ai1b:NOPE"}, headers=analyst.headers)
    assert missing.status_code == 404 and len(mock.calls) == 1
    anonymous = client.post(URL, json={"question": "summary", "account_id": "ai1b:A"})
    assert anonymous.status_code == 401 and len(mock.calls) == 1
