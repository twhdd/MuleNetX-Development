"""Permission matrix and case field/transition rules (SRS §22.2), as data."""

from __future__ import annotations

from typing import Final, Literal

Role = Literal["ADMIN", "INVESTIGATOR", "ANALYST"]
ROLES: Final[tuple[Role, ...]] = ("ADMIN", "INVESTIGATOR", "ANALYST")

A, D = True, False

# permission -> {role: allowed}. "ALLOW (restricted below)" and "ALLOW (participant only)" are ALLOW here;
# the participant restriction is enforced by the case field rules and InvestigationService.
PERMISSIONS: Final[dict[str, dict[Role, bool]]] = {
    "account.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "transaction.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "graph.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "graph.analytics.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "risk.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "shap.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "temporal.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "motif.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "money_flow.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "community.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "ring.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "ring.review": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": D},
    "intervention.simulate": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "evaluation.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "model.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "case.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "case.create": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "case.update": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "case.assign": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": D},
    "case.resolve": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": D},
    "case_subject.manage": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "finding.create": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "copilot.use": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "ingestion.create": {"ADMIN": A, "INVESTIGATOR": D, "ANALYST": D},
    "ingestion.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "pipeline.read": {"ADMIN": A, "INVESTIGATOR": A, "ANALYST": A},
    "pipeline.control": {"ADMIN": A, "INVESTIGATOR": D, "ANALYST": D},
    "audit.read": {"ADMIN": A, "INVESTIGATOR": D, "ANALYST": D},
    "user.read": {"ADMIN": A, "INVESTIGATOR": D, "ANALYST": D},
    "user.manage": {"ADMIN": A, "INVESTIGATOR": D, "ANALYST": D},
    "role.manage": {"ADMIN": A, "INVESTIGATOR": D, "ANALYST": D},
    "system_config.read": {"ADMIN": A, "INVESTIGATOR": D, "ANALYST": D},
    "system_config.write": {"ADMIN": A, "INVESTIGATOR": D, "ANALYST": D},
}

# Permissions restricted to case participants (creator or assignee) for the ANALYST role.
PARTICIPANT_ONLY: Final[dict[str, frozenset[Role]]] = {
    "case_subject.manage": frozenset({"ANALYST"}),
    "finding.create": frozenset({"ANALYST"}),
}

Scope = Literal["any", "participant", "deny"]

# Case field and transition rules (SRS §22.2). Keys: field names, or "FROM->TO" transitions.
CASE_FIELD_RULES: Final[dict[str, dict[Role, Scope]]] = {
    "title": {"ADMIN": "any", "INVESTIGATOR": "any", "ANALYST": "participant"},
    "priority": {"ADMIN": "any", "INVESTIGATOR": "any", "ANALYST": "participant"},
    "assigned_to": {"ADMIN": "any", "INVESTIGATOR": "any", "ANALYST": "deny"},
    "OPEN->IN_REVIEW": {"ADMIN": "any", "INVESTIGATOR": "any", "ANALYST": "participant"},
    "IN_REVIEW->ESCALATED": {"ADMIN": "any", "INVESTIGATOR": "any", "ANALYST": "participant"},
    "->RESOLVED": {"ADMIN": "any", "INVESTIGATOR": "any", "ANALYST": "deny"},
    "->FALSE_POSITIVE": {"ADMIN": "any", "INVESTIGATOR": "any", "ANALYST": "deny"},
    "->CLOSED": {"ADMIN": "any", "INVESTIGATOR": "any", "ANALYST": "deny"},
    "ESCALATED->IN_REVIEW": {"ADMIN": "any", "INVESTIGATOR": "any", "ANALYST": "deny"},
}


def is_allowed(role: str, permission: str) -> bool:
    rules = PERMISSIONS.get(permission)
    if rules is None:
        raise KeyError(f"unknown permission {permission}")
    return bool(rules.get(role, False))  # type: ignore[call-overload]


def transition_rule_key(from_state: str, to_state: str) -> str:
    if to_state in ("RESOLVED", "FALSE_POSITIVE", "CLOSED"):
        return f"->{to_state}"
    return f"{from_state}->{to_state}"
