"""AT-AI-05: while a generation holds the single slot, a second request waits 2 s then gets 429 COPILOT_BUSY;
a user's seventh request within a minute gets 429 RATE_LIMITED (SRS §21.7)."""

import threading
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.copilotutil import MockOllama, install
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration

URL = "/api/v1/copilot/query"


def test_AT_AI_05_busy(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("A", "B", 40.0, 1)], key="ai5")
    mock = MockOllama()
    entered, release = threading.Event(), threading.Event()

    def held(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/chat":
            entered.set()
            release.wait(30)
        return mock.handler(request)

    install(app, mock, transport=httpx.MockTransport(held))
    first_user, second_user = users("ANALYST"), users("INVESTIGATOR")
    results: dict[str, int] = {}

    def first() -> None:
        with TestClient(app) as c:
            r = c.post(URL, json={"question": "summary", "account_id": "ai5:A"}, headers=first_user.headers)
            results["first"] = r.status_code

    t = threading.Thread(target=first)
    t.start()
    try:
        assert entered.wait(30)
        started = time.monotonic()
        second = client.post(URL, json={"question": "summary", "account_id": "ai5:A"}, headers=second_user.headers)
        waited = time.monotonic() - started
    finally:
        release.set()
        t.join(30)
    assert second.status_code == 429 and second.json()["error"]["code"] == "COPILOT_BUSY"
    assert waited >= 2.0
    assert results["first"] == 200
    # once the slot is free, the next request is served
    ok = client.post(URL, json={"question": "summary", "account_id": "ai5:A"}, headers=second_user.headers)
    assert ok.status_code == 200, ok.text


def test_AT_AI_05_rate_limited(app, client, users) -> None:
    admin = users("ADMIN")
    seed_and_activate(app, client, admin, [("A", "B", 40.0, 1)], key="ai5b")
    mock = install(app)
    analyst = users("ANALYST")
    codes = [
        client.post(URL, json={"question": "summary", "account_id": "ai5b:A"}, headers=analyst.headers).status_code
        for _ in range(7)
    ]
    assert codes[:6] == [200] * 6
    assert codes[6] == 429
    assert len(mock.calls) == 6
    # the limit is per user
    other = users("INVESTIGATOR")
    assert (
        client.post(URL, json={"question": "summary", "account_id": "ai5b:A"}, headers=other.headers).status_code == 200
    )


def test_AT_AI_05_limiter_window() -> None:
    import uuid

    from mulenetx.copilot.limiter import Limiter
    from mulenetx.core.errors import AppError

    limiter, user = Limiter(1, 0.1, 6), uuid.uuid4()
    for i in range(6):
        limiter.check_rate(user, now=100.0 + i)
    with pytest.raises(AppError) as exc:
        limiter.check_rate(user, now=110.0)
    assert exc.value.code == "RATE_LIMITED"
    limiter.check_rate(user, now=160.0)  # the first call has left the 60 s window
