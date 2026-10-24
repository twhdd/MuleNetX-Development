"""The permission matrix equals SRS §22.2 row by row (SRS §27.1: RBAC, every permission × role)."""

import re
from pathlib import Path

from mulenetx.auth.permissions import CASE_FIELD_RULES, PERMISSIONS, ROLES, is_allowed

SRS = Path(__file__).resolve().parents[3] / "docs" / "SRS.md"


def _srs_matrix() -> dict[str, dict[str, bool]]:
    text = SRS.read_text(encoding="utf-8")
    section = text[text.index("## 22.2 Permission Matrix") : text.index("**Case field and transition rules**")]
    rows: dict[str, dict[str, bool]] = {}
    for line in section.splitlines():
        m = re.match(r"^\| ([a-z_.]+) \| (\w+)[^|]* \| (\w+)[^|]* \| (\w+)[^|]* \|$", line)
        if m:
            rows[m.group(1)] = {r: m.group(i + 2) == "ALLOW" for i, r in enumerate(ROLES)}
    return rows


def test_matrix_matches_srs_row_by_row() -> None:
    srs = _srs_matrix()
    assert len(srs) == 33
    assert {k: dict(v) for k, v in PERMISSIONS.items()} == srs


def test_every_permission_and_role_explicit() -> None:
    for permission, rules in PERMISSIONS.items():
        assert set(rules) == set(ROLES), permission
        for role in ROLES:
            assert is_allowed(role, permission) == rules[role]


def test_case_field_rules_match_srs() -> None:
    assert CASE_FIELD_RULES["title"]["ANALYST"] == "participant"
    assert CASE_FIELD_RULES["assigned_to"]["ANALYST"] == "deny"
    assert CASE_FIELD_RULES["OPEN->IN_REVIEW"]["ANALYST"] == "participant"
    assert CASE_FIELD_RULES["IN_REVIEW->ESCALATED"]["ANALYST"] == "participant"
    for key in ("->RESOLVED", "->FALSE_POSITIVE", "->CLOSED", "ESCALATED->IN_REVIEW"):
        assert CASE_FIELD_RULES[key] == {"ADMIN": "any", "INVESTIGATOR": "any", "ANALYST": "deny"}
