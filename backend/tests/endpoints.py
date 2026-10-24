"""Registry of implemented protected endpoints with their SRS §19.2 permission.

Each task adds its endpoints. Used by AT-SEC-01 (unauthenticated), AT-SEC-04 (role denials) and the
inventory test. Path parameters use placeholder IDs; permission checks run before resource lookups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PLACEHOLDER = "00000000-0000-4000-8000-000000000000"


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    permission: str  # "authenticated" for endpoints that only need a session
    body: dict[str, Any] | None = None
    params: dict[str, Any] = field(default_factory=dict)
    also: tuple[str, ...] = ()  # other permissions checked first on the same endpoint

    @property
    def url(self) -> str:
        return (
            self.path.replace("{id}", PLACEHOLDER)
            .replace("{version}", "v0")
            .replace("{type}", "ACCOUNT")
            .replace("{subject_id}", "x")
            .replace("{level}", "RING")
        )


ENDPOINTS: list[Endpoint] = [
    Endpoint("POST", "/api/v1/auth/logout", "authenticated"),
    Endpoint("GET", "/api/v1/auth/me", "authenticated"),
    Endpoint("GET", "/api/v1/users", "user.read"),
    Endpoint("POST", "/api/v1/users", "user.manage", {"username": "x-user", "role": "ANALYST", "password": "p" * 16}),
    Endpoint("PATCH", "/api/v1/users/{id}", "user.manage", {"is_active": True}),
    Endpoint("PATCH", "/api/v1/users/{id}", "role.manage", {"role": "ANALYST"}, also=("user.manage",)),
    Endpoint("POST", "/api/v1/ingestion", "ingestion.create"),
    Endpoint("GET", "/api/v1/ingestion", "ingestion.read"),
    Endpoint("GET", "/api/v1/ingestion/{id}", "ingestion.read"),
    Endpoint("GET", "/api/v1/datasets/{id}/profile", "ingestion.read"),
    Endpoint("GET", "/api/v1/pipeline-runs", "pipeline.read"),
    Endpoint("GET", "/api/v1/pipeline-runs/{id}", "pipeline.read"),
    Endpoint("POST", "/api/v1/pipeline-runs", "pipeline.control", {"dataset_id": PLACEHOLDER}),
    Endpoint("POST", "/api/v1/pipeline-runs/{id}/retry", "pipeline.control"),
    Endpoint("GET", "/api/v1/models", "model.read"),
    Endpoint("GET", "/api/v1/models/{version}", "model.read"),
    Endpoint("GET", "/api/v1/context", "account.read"),
    Endpoint("POST", "/api/v1/ingestion/{id}/retry", "pipeline.control"),
    Endpoint("GET", "/api/v1/accounts", "account.read"),
    Endpoint("GET", "/api/v1/accounts/{id}", "account.read"),
    Endpoint("GET", "/api/v1/accounts/{id}/transactions", "transaction.read"),
    Endpoint("GET", "/api/v1/accounts/{id}/risk", "risk.read"),
    Endpoint("GET", "/api/v1/accounts/{id}/risk/history", "risk.read"),
    Endpoint("GET", "/api/v1/accounts/{id}/risk/propagation", "risk.read"),
    Endpoint("GET", "/api/v1/accounts/{id}/features", "risk.read"),
    Endpoint("GET", "/api/v1/accounts/{id}/temporal", "temporal.read"),
    Endpoint("GET", "/api/v1/accounts/{id}/shap", "shap.read"),
    Endpoint("GET", "/api/v1/graph/neighborhood", "graph.read", params={"account_id": "x:CA"}),
    Endpoint("GET", "/api/v1/graph/metrics", "graph.analytics.read", params={"account_id": "x:CA"}),
    Endpoint(
        "GET",
        "/api/v1/graph/path",
        "money_flow.read",
        params={"source_account_id": "x:A", "destination_account_id": "x:B"},
    ),
    Endpoint(
        "GET",
        "/api/v1/graph/paths/{id}",
        "money_flow.read",
        params={"graph_snapshot_id": PLACEHOLDER, "accounts": "x:A,x:B"},
    ),
    Endpoint(
        "GET",
        "/api/v1/money-flow",
        "money_flow.read",
        params={"source_account_id": "x:A", "destination_account_id": "x:B"},
    ),
    Endpoint("GET", "/api/v1/communities", "community.read"),
    Endpoint("GET", "/api/v1/communities/{id}", "community.read"),
    Endpoint("GET", "/api/v1/accounts/{id}/community", "community.read"),
    Endpoint("GET", "/api/v1/cases", "case.read"),
    Endpoint("POST", "/api/v1/cases", "case.create", {"title": "t", "priority": "LOW"}),
    Endpoint("GET", "/api/v1/cases/{id}", "case.read"),
    Endpoint("PATCH", "/api/v1/cases/{id}", "case.update", {"version": 1}),
    Endpoint("GET", "/api/v1/cases/{id}/subjects", "case.read"),
    Endpoint(
        "POST", "/api/v1/cases/{id}/subjects", "case_subject.manage", {"subject_type": "ACCOUNT", "subject_id": "x"}
    ),
    Endpoint("DELETE", "/api/v1/cases/{id}/subjects/{type}/{subject_id}", "case_subject.manage"),
    Endpoint(
        "POST",
        "/api/v1/cases/{id}/findings",
        "finding.create",
        {"type": "t", "description": "d", "evidence": [], "source": "s"},
    ),
    Endpoint("GET", "/api/v1/cases/{id}/findings", "case.read"),
    Endpoint("GET", "/api/v1/audit", "audit.read"),
    Endpoint("GET", "/api/v1/accounts/{id}/motifs", "motif.read"),
    Endpoint("GET", "/api/v1/rings/{id}/motifs", "motif.read"),
    Endpoint("GET", "/api/v1/rings", "ring.read"),
    Endpoint("GET", "/api/v1/rings/{id}", "ring.read"),
    Endpoint("PATCH", "/api/v1/rings/{id}/status", "ring.review", {"status": "REVIEWED"}),
    Endpoint("GET", "/api/v1/rings/{id}/accounts", "ring.read"),
    Endpoint("GET", "/api/v1/rings/{id}/transactions", "ring.read"),
    Endpoint("GET", "/api/v1/rings/{id}/features", "ring.read"),
    Endpoint("GET", "/api/v1/rings/{id}/risk", "ring.read"),
    Endpoint("GET", "/api/v1/rings/{id}/evidence", "ring.read"),
    Endpoint("GET", "/api/v1/fraud-ring-candidates", "ring.read"),
    Endpoint("GET", "/api/v1/fraud-ring-candidates/{id}", "ring.read"),
    Endpoint("POST", "/api/v1/rings/{id}/interventions/simulate", "intervention.simulate", {"mode": "RANK"}),
    Endpoint("GET", "/api/v1/rings/{id}/interventions", "ring.read"),
    Endpoint("GET", "/api/v1/interventions/{id}", "ring.read"),
    Endpoint("GET", "/api/v1/interventions/{id}/candidates", "ring.read"),
    Endpoint("POST", "/api/v1/evaluation/runs", "pipeline.control", {}),
    Endpoint("GET", "/api/v1/evaluation/runs", "evaluation.read"),
    Endpoint("GET", "/api/v1/evaluation/runs/{id}", "evaluation.read"),
    Endpoint("GET", "/api/v1/evaluation/runs/{id}/{level}", "evaluation.read"),
    Endpoint("GET", "/api/v1/evaluation/summary", "evaluation.read"),
    Endpoint("GET", "/api/v1/evaluation/{level}", "evaluation.read"),
    Endpoint("POST", "/api/v1/copilot/query", "copilot.use", {"question": "q"}),
]
