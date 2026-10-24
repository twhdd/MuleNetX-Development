"""Stable error codes (SRS §19.3) with their HTTP status and default message.

The SRS names the domain codes; the generic codes for standard statuses are a PLAN DEFAULT (§3.6).
No other code may be added without an SRS change. `docs/api-errors.md` is generated from this table.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    http_status: int
    message: str


# ── Domain codes named in the SRS ───────────────────────────────────────────
LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
INVALID_PATH_REQUEST = "INVALID_PATH_REQUEST"
INTERVENTION_TARGET_INVALID = "INTERVENTION_TARGET_INVALID"
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
RISK_NOT_AVAILABLE = "RISK_NOT_AVAILABLE"
EXPLANATION_NOT_AVAILABLE = "EXPLANATION_NOT_AVAILABLE"
EVALUATION_NOT_AVAILABLE = "EVALUATION_NOT_AVAILABLE"
QUERY_TIMEOUT = "QUERY_TIMEOUT"
CASE_VERSION_CONFLICT = "CASE_VERSION_CONFLICT"
INVALID_CASE_TRANSITION = "INVALID_CASE_TRANSITION"
DATASET_ALREADY_REGISTERED = "DATASET_ALREADY_REGISTERED"
EXPLANATION_VERSION_MISMATCH = "EXPLANATION_VERSION_MISMATCH"
PIPELINE_ALREADY_RUNNING = "PIPELINE_ALREADY_RUNNING"
PIPELINE_PREREQUISITE_MISSING = "PIPELINE_PREREQUISITE_MISSING"
RING_INTELLIGENCE_NOT_APPLICABLE = "RING_INTELLIGENCE_NOT_APPLICABLE"
SCENARIO_NOT_COMPLETED = "SCENARIO_NOT_COMPLETED"
SNAPSHOT_RETIRED = "SNAPSHOT_RETIRED"
COPILOT_BUSY = "COPILOT_BUSY"
AI_RESPONSE_INVALID = "AI_RESPONSE_INVALID"
COPILOT_UNAVAILABLE = "COPILOT_UNAVAILABLE"
GRAPH_UNAVAILABLE = "GRAPH_UNAVAILABLE"
MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"

# ── Generic codes for standard statuses [PLAN DEFAULT §3.6] ────────────────
VALIDATION_ERROR = "VALIDATION_ERROR"
UNAUTHENTICATED = "UNAUTHENTICATED"
FORBIDDEN = "FORBIDDEN"
NOT_FOUND = "NOT_FOUND"
CONFLICT = "CONFLICT"
PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
RATE_LIMITED = "RATE_LIMITED"
INTERNAL = "INTERNAL"
DB_UNAVAILABLE = "DB_UNAVAILABLE"

ERRORS: dict[str, ErrorSpec] = {
    spec.code: spec
    for spec in (
        ErrorSpec(LIMIT_EXCEEDED, 400, "The requested operation exceeds the permitted limit."),
        ErrorSpec(INVALID_PATH_REQUEST, 400, "Source and destination accounts must differ."),
        ErrorSpec(INTERVENTION_TARGET_INVALID, 400, "The intervention targets are not valid for this ring."),
        ErrorSpec(INVALID_CREDENTIALS, 401, "Invalid credentials."),
        ErrorSpec(RISK_NOT_AVAILABLE, 404, "No risk assessment is available for this account."),
        ErrorSpec(EXPLANATION_NOT_AVAILABLE, 404, "No model explanation is available for this assessment."),
        ErrorSpec(EVALUATION_NOT_AVAILABLE, 404, "No completed evaluation run is available."),
        ErrorSpec(QUERY_TIMEOUT, 408, "The query exceeded its time limit."),
        ErrorSpec(CASE_VERSION_CONFLICT, 409, "The case was changed by another request; reload and retry."),
        ErrorSpec(INVALID_CASE_TRANSITION, 409, "The requested case status transition is not allowed."),
        ErrorSpec(DATASET_ALREADY_REGISTERED, 409, "This file is already registered under this dataset version."),
        ErrorSpec(EXPLANATION_VERSION_MISMATCH, 409, "The explanation does not match the assessment versions."),
        ErrorSpec(PIPELINE_ALREADY_RUNNING, 409, "A pipeline run is already active for this dataset."),
        ErrorSpec(PIPELINE_PREREQUISITE_MISSING, 409, "A prerequisite of the requested stage is missing."),
        ErrorSpec(
            RING_INTELLIGENCE_NOT_APPLICABLE,
            409,
            "Ring intelligence is not computed for a suspicious community candidate.",
        ),
        ErrorSpec(SCENARIO_NOT_COMPLETED, 409, "The simulation scenario has not completed."),
        ErrorSpec(SNAPSHOT_RETIRED, 410, "The requested graph snapshot has been retired."),
        ErrorSpec(COPILOT_BUSY, 429, "The copilot is busy; retry shortly."),
        ErrorSpec(AI_RESPONSE_INVALID, 503, "The copilot response failed validation and was discarded."),
        ErrorSpec(COPILOT_UNAVAILABLE, 503, "The copilot is unavailable."),
        ErrorSpec(GRAPH_UNAVAILABLE, 503, "The graph store is unavailable."),
        ErrorSpec(MODEL_UNAVAILABLE, 503, "The model artifact is unavailable."),
        ErrorSpec(VALIDATION_ERROR, 400, "The request is invalid."),
        ErrorSpec(UNAUTHENTICATED, 401, "Authentication is required."),
        ErrorSpec(FORBIDDEN, 403, "You do not have permission to perform this action."),
        ErrorSpec(NOT_FOUND, 404, "The requested resource was not found."),
        ErrorSpec(CONFLICT, 409, "The request conflicts with the current state."),
        ErrorSpec(PAYLOAD_TOO_LARGE, 413, "The request body is too large."),
        ErrorSpec(UNSUPPORTED_MEDIA_TYPE, 415, "The content type is not supported."),
        ErrorSpec(RATE_LIMITED, 429, "Too many requests."),
        ErrorSpec(INTERNAL, 500, "An internal error occurred."),
        ErrorSpec(DB_UNAVAILABLE, 503, "The database is unavailable."),
    )
}

GENERIC_BY_STATUS: dict[int, str] = {
    400: VALIDATION_ERROR,
    401: UNAUTHENTICATED,
    403: FORBIDDEN,
    404: NOT_FOUND,
    409: CONFLICT,
    413: PAYLOAD_TOO_LARGE,
    415: UNSUPPORTED_MEDIA_TYPE,
    429: RATE_LIMITED,
    500: INTERNAL,
    503: DB_UNAVAILABLE,
}


DOMAIN_CODES: frozenset[str] = frozenset(c for c in ERRORS if c not in GENERIC_BY_STATUS.values())


def catalogue_markdown() -> str:
    """The error catalogue (`docs/api-errors.md`), generated from ERRORS."""
    lines = [
        "# API error codes",
        "",
        "Generated by `mulenetx.cli export-errors` from `backend/mulenetx/core/error_codes.py`; do not edit.",
        "",
        "Every error response uses the SRS §19.3 envelope:",
        "",
        "```json",
        '{"error": {"code": "...", "message": "...", "request_id": "...", "details": {}}}',
        "```",
        "",
        "Messages are safe defaults; `details` carries structured context (for example the field and limit of",
        "`LIMIT_EXCEEDED`). Generic codes for standard statuses are a PLAN default (§3.6); the others are named",
        "by the SRS.",
        "",
        "| Code | HTTP | Kind | Default message |",
        "|---|---|---|---|",
    ]
    for spec in sorted(ERRORS.values(), key=lambda e: (e.http_status, e.code)):
        kind = "domain (SRS)" if spec.code in DOMAIN_CODES else "generic"
        lines.append(f"| `{spec.code}` | {spec.http_status} | {kind} | {spec.message} |")
    return "\n".join(lines) + "\n"
