"""AT-SEC-04: every DENY of the SRS §22.2 matrix returns 403 and writes a DENIED audit event, for every
endpoint guarded by that permission. The registry (tests/endpoints.py) covers every route (AT-SEC-01 checks
that), and field and participant rules are in tests/security/test_case_mutation_matrix.py."""

import pytest

from mulenetx.auth.permissions import PERMISSIONS, ROLES
from tests.apiutil import audit_events
from tests.endpoints import ENDPOINTS

pytestmark = pytest.mark.integration

DENIALS = [
    (role, e) for e in ENDPOINTS if e.permission in PERMISSIONS for role in ROLES if not PERMISSIONS[e.permission][role]
]


@pytest.mark.parametrize(
    ("role", "endpoint"), DENIALS, ids=[f"{r}-{e.method}-{e.path}-{e.permission}" for r, e in DENIALS]
)
def test_AT_SEC_04_role_denied(app, client, users, role, endpoint) -> None:
    actor = users(role)
    before = len(audit_events(app, "authz.denied", "DENIED"))
    resp = client.request(
        endpoint.method, endpoint.url, headers=actor.headers, json=endpoint.body, params=endpoint.params
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["code"] == "FORBIDDEN"
    denied = audit_events(app, "authz.denied", "DENIED")
    assert len(denied) == before + 1
    assert denied[-1].user_id == actor.user_id
    assert denied[-1].metadata_["permission"] in (endpoint.permission, *endpoint.also)


def test_AT_SEC_04_has_denials() -> None:
    assert len(DENIALS) >= 6
