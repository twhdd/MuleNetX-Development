"""Unauthorized case mutations and field changes per role (SRS §22.2, §27.6), from the rule tables themselves:
every field and transition of CASE_FIELD_RULES and every participant-only permission, for ADMIN, INVESTIGATOR,
an ANALYST participant and an ANALYST outsider. Denials are 403 and audited; allowed changes apply."""

from typing import Any

import pytest

from mulenetx.auth.permissions import CASE_FIELD_RULES, PARTICIPANT_ONLY
from tests.apiutil import audit_events
from tests.caseutil import new_case, patch
from tests.ingestutil import seed_and_activate

pytestmark = pytest.mark.integration

ACTORS = ["ADMIN", "INVESTIGATOR", "ANALYST_PARTICIPANT", "ANALYST_OUTSIDER"]
# rule key -> (state to start from, change to attempt)
CHANGES: dict[str, tuple[str, dict[str, Any]]] = {
    "title": ("OPEN", {"title": "Changed"}),
    "priority": ("OPEN", {"priority": "LOW"}),
    "assigned_to": ("OPEN", {}),  # filled per test with a fresh user, so it is a real change
    "OPEN->IN_REVIEW": ("OPEN", {"status": "IN_REVIEW"}),
    "IN_REVIEW->ESCALATED": ("IN_REVIEW", {"status": "ESCALATED"}),
    "->RESOLVED": ("IN_REVIEW", {"status": "RESOLVED"}),
    "->FALSE_POSITIVE": ("IN_REVIEW", {"status": "FALSE_POSITIVE"}),
    "->CLOSED": ("RESOLVED", {"status": "CLOSED"}),
    "ESCALATED->IN_REVIEW": ("ESCALATED", {"status": "IN_REVIEW"}),
}
PATH = {
    "OPEN": [],
    "IN_REVIEW": ["IN_REVIEW"],
    "ESCALATED": ["IN_REVIEW", "ESCALATED"],
    "RESOLVED": ["IN_REVIEW", "RESOLVED"],
}


def test_matrix_covers_every_rule() -> None:
    assert set(CHANGES) == set(CASE_FIELD_RULES)


def allowed(rule: dict[str, str], actor: str) -> bool:
    scope = rule["ANALYST" if actor.startswith("ANALYST") else actor]
    return scope == "any" or (scope == "participant" and actor == "ANALYST_PARTICIPANT")


def setup(client: Any, users: Any, actor: str, state: str) -> tuple[Any, dict[str, Any]]:
    owner = users("INVESTIGATOR")
    person = users("ANALYST" if actor.startswith("ANALYST") else actor)
    case = new_case(client, owner)
    if actor == "ANALYST_PARTICIPANT":
        case = patch(client, owner, case, assigned_to=str(person.user_id)).json()
    for step in PATH[state]:
        resp = patch(client, owner, case, status=step)
        assert resp.status_code == 200, resp.text
        case = resp.json()
    return person, case


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("key", list(CHANGES))
def test_case_field_rule(app, client, users, key, actor) -> None:
    state, change = CHANGES[key]
    person, case = setup(client, users, actor, state)
    if key == "assigned_to":
        change = {"assigned_to": str(users("INVESTIGATOR").user_id)}
    denied_before = len(audit_events(app, "authz.denied", "DENIED"))
    resp = patch(client, person, case, **change)
    if allowed(CASE_FIELD_RULES[key], actor):
        assert resp.status_code == 200, f"{actor} {key}: {resp.text}"
        for field, value in change.items():
            assert resp.json()[field] == value
    else:
        assert resp.status_code == 403, f"{actor} {key}: {resp.status_code} {resp.text}"
        assert len(audit_events(app, "authz.denied", "DENIED")) == denied_before + 1
        after = client.get(f"/api/v1/cases/{case['case_id']}", headers=person.headers).json()
        assert after["version"] == case["version"]


@pytest.mark.parametrize("actor", ACTORS)
@pytest.mark.parametrize("permission", sorted(PARTICIPANT_ONLY))
def test_participant_only_permission(app, client, users, permission, actor) -> None:
    seed_and_activate(app, client, users("ADMIN"), [("A", "B", 1.0, 1)], key="cm")
    person, case = setup(client, users, actor, "OPEN")
    url = f"/api/v1/cases/{case['case_id']}"
    if permission == "case_subject.manage":
        resp = client.post(
            f"{url}/subjects", json={"subject_type": "ACCOUNT", "subject_id": "cm:A"}, headers=person.headers
        )
    else:
        resp = client.post(
            f"{url}/findings", json={"type": "NOTE", "description": "d", "source": "s"}, headers=person.headers
        )
    restricted = actor.startswith("ANALYST") and "ANALYST" in PARTICIPANT_ONLY[permission]
    if restricted and actor == "ANALYST_OUTSIDER":
        assert resp.status_code == 403, resp.text
        denied = audit_events(app, "authz.denied", "DENIED")
        assert denied and denied[-1].user_id == person.user_id
    else:
        assert resp.status_code == 201, resp.text
