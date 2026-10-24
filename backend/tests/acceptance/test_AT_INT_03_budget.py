"""AT-INT-03 (§27.10 check 4): k_max is enforced and invalid EVALUATE targets return 400
INTERVENTION_TARGET_INVALID before any scenario exists; suspicious communities take no simulation."""

import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from tests.apiutil import _Req
from tests.ringapi import rings_by_class
from tests.scenarioutil import simulate

pytestmark = pytest.mark.integration


def test_AT_INT_03_budget(app, client, users) -> None:
    rings = rings_by_class(app, client, users("ADMIN"), "i3")
    ring = rings["POTENTIAL_FRAUD_RING_CANDIDATE"]
    inv = users("INVESTIGATOR")
    members = [
        m["account_id"]
        for m in client.get(
            f"/api/v1/rings/{ring['ring_id']}/accounts", params={"page_size": 10}, headers=inv.headers
        ).json()["items"]
    ]
    cases = [
        {"mode": "EVALUATE", "intervention_type": "ACCOUNT_SET_REMOVAL", "target_ids": [*members[:3], "x:4th"][:4]},
        {"mode": "EVALUATE", "intervention_type": "ACCOUNT_SET_REMOVAL", "target_ids": [members[0], members[0]]},
        {"mode": "EVALUATE", "intervention_type": "ACCOUNT_REMOVAL", "target_ids": []},
        {"mode": "EVALUATE", "intervention_type": "ACCOUNT_REMOVAL", "target_ids": ["not:an-account"]},
        {"mode": "EVALUATE", "intervention_type": "EDGE_REMOVAL", "target_ids": ["x>y"]},
        {"mode": "RANK", "target_ids": [members[0]]},
    ]
    for body in cases:
        resp = simulate(client, inv, ring["ring_id"], body)
        assert resp.status_code == 400, (body, resp.text)
        assert resp.json()["error"]["code"] == "INTERVENTION_TARGET_INVALID", body
    for body in ({"mode": "BLOCK"}, {"mode": "RANK", "freeze_accounts": True}):
        assert simulate(client, inv, ring["ring_id"], body).status_code == 400  # no real-action field exists
    sc = simulate(client, inv, rings["SUSPICIOUS_COMMUNITY"]["ring_id"], {"mode": "RANK"})
    assert sc.status_code == 409 and sc.json()["error"]["code"] == "RING_INTELLIGENCE_NOT_APPLICABLE"
    rt = get_services(_Req(app)).runtime
    with rt.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM intervention_scenarios")).scalar_one() == 0
        assert conn.execute(text("SELECT count(*) FROM jobs WHERE kind = 'INTERVENTION'")).scalar_one() == 0
