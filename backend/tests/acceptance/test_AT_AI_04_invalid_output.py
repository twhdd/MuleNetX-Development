"""AT-AI-04: simulated model output with an invented reference, an uncited fact, a deny-list phrase, unparseable
JSON or an over-long answer is rejected with 503 AI_RESPONSE_INVALID (SRS §21.6)."""

import pytest

from tests.apiutil import audit_events
from tests.copilotutil import MockOllama, grounded, install
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration

URL = "/api/v1/copilot/query"


def invented_ref(ctx):
    out = grounded(ctx)
    out["facts"][0]["refs"] = ["account:ai4:DOES_NOT_EXIST"]
    return out


def invented_source_reference(ctx):
    out = grounded(ctx)
    out["source_references"] = [*out["source_references"], "transaction:made-up"]
    return out


def uncited_fact(ctx):
    out = grounded(ctx)
    out["facts"].append({"text": "The account received 12 transfers.", "refs": []})
    return out


def uncited_signal(ctx):
    out = grounded(ctx)
    out["observed_signals"] = [{"text": "Velocity is elevated.", "refs": []}]
    return out


def deny_phrase(ctx):
    out = grounded(ctx)
    out["possible_interpretation"] = [{"text": "This account is a money mule.", "refs": out["source_references"][:1]}]
    return out


def deny_phrase_in_limitations(ctx):
    out = grounded(ctx)
    out["limitations"] = ["The account should be frozen pending review."]
    return out


def not_json(ctx):
    return "Sure! Here is my analysis: the account looks suspicious."


def wrong_shape(ctx):
    return {"facts": "none", "observed_signals": []}


CASES = {
    "invented-ref": (invented_ref, 2),
    "invented-source-reference": (invented_source_reference, 2),
    "uncited-fact": (uncited_fact, 3),
    "uncited-signal": (uncited_signal, 3),
    "deny-phrase": (deny_phrase, 4),
    "deny-phrase-limitations": (deny_phrase_in_limitations, 4),
    "not-json": (not_json, 1),
    "wrong-shape": (wrong_shape, 1),
}


@pytest.mark.parametrize("name", list(CASES))
def test_AT_AI_04_invalid_output(app, client, users, name) -> None:
    answer, rule = CASES[name]
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("A", "B", 40.0, 1), ("B", "C", 39.0, 2)], key="ai4")
    install(app, MockOllama(answer))
    analyst = users("ANALYST")
    resp = client.post(URL, json={"question": "Why is this risky?", "account_id": "ai4:B"}, headers=analyst.headers)
    assert resp.status_code == 503, resp.text
    err = resp.json()["error"]
    assert err["code"] == "AI_RESPONSE_INVALID" and err["details"]["rule"] == rule
    event = audit_events(app, action="copilot.query")[-1]
    assert event.outcome == "FAILED" and event.metadata_["validation_rule"] == rule


def test_AT_AI_04_output_token_limit(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("A", "B", 40.0, 1)], key="ai4b")
    mock = install(app)
    original = mock.handler

    def over_limit(request):
        resp = original(request)
        if request.url.path == "/api/chat":
            body = resp.json()
            body["eval_count"] = 5000
            import httpx

            return httpx.Response(200, json=body)
        return resp

    import httpx

    install(app, transport=httpx.MockTransport(over_limit))
    analyst = users("ANALYST")
    resp = client.post(URL, json={"question": "summary", "account_id": "ai4b:A"}, headers=analyst.headers)
    assert resp.status_code == 503 and resp.json()["error"]["details"]["rule"] == 5


def test_AT_AI_04_quoted_context_text_is_allowed(app, client, users) -> None:
    """A deny-list phrase quoted verbatim from the context (e.g. a finding's own words) is not the model's claim."""
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("A", "B", 40.0, 1)], key="ai4c")
    inv = users("INVESTIGATOR")
    case = client.post("/api/v1/cases", json={"title": "Review", "priority": "LOW"}, headers=inv.headers).json()
    cid = case["case_id"]
    note = {"type": "NOTE", "description": "Customer said the account is a mule for a friend.", "source": "call"}
    assert client.post(f"/api/v1/cases/{cid}/findings", json=note, headers=inv.headers).status_code == 201

    def quoting(ctx):
        ref = ctx["findings"][0]["ref"]
        return {
            "facts": [
                {"text": 'A finding records: "Customer said the account is a mule for a friend."', "refs": [ref]}
            ],
            "observed_signals": [],
            "possible_interpretation": [],
            "limitations": ["The finding is a reported statement, not a determination."],
            "source_references": [ref],
        }

    install(app, MockOllama(quoting))
    resp = client.post(URL, json={"question": "Summarise the case", "case_id": cid}, headers=inv.headers)
    assert resp.status_code == 200, resp.text
