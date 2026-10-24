"""AT-INT-10: a user with 2 queued or running scenarios gets 429 on a third; others are unaffected."""

import pytest

from tests.apiutil import audit_events
from tests.scenarioutil import potential_ring, simulate

pytestmark = pytest.mark.integration


def test_AT_INT_10_concurrency_limit(app, client, users) -> None:
    ring = potential_ring(app, client, users("ADMIN"), "i10")
    inv = users("INVESTIGATOR")
    for _ in range(2):
        assert simulate(client, inv, ring["ring_id"], {"mode": "RANK"}).status_code == 202
    third = simulate(client, inv, ring["ring_id"], {"mode": "RANK"})
    assert third.status_code == 429 and third.json()["error"]["details"]["limit"] == 2
    other = users("ANALYST")  # intervention.simulate is allowed for analysts (§22.2)
    assert simulate(client, other, ring["ring_id"], {"mode": "RANK"}).status_code == 202
    assert len(audit_events(app, "intervention.create", "SUCCESS")) == 3
