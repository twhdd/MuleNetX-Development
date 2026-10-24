"""AT-INV-04: a PATCH with a stale version returns 409 CASE_VERSION_CONFLICT (optimistic concurrency)."""

import pytest

from tests.caseutil import new_case, patch

pytestmark = pytest.mark.integration


def test_AT_INV_04_version_conflict(client, users) -> None:
    inv = users("INVESTIGATOR")
    case = new_case(client, inv)
    updated = patch(client, inv, case, title="Updated title").json()
    assert updated["version"] == 2
    stale = patch(client, inv, case, priority="LOW")  # still carries version 1
    assert stale.status_code == 409 and stale.json()["error"]["code"] == "CASE_VERSION_CONFLICT"
    assert patch(client, inv, updated, priority="LOW").json()["version"] == 3
    unchanged = patch(client, inv, {**updated, "version": 3}, priority="LOW").json()
    assert unchanged["version"] == 3  # no effective change → no new version
