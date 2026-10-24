"""PostgreSQL job queue (SRS §7.8, PLAN §7.2).

Enqueue happens inside the caller's transaction so that the resource row and its job commit together
before the API answers 202. Claiming is one statement with `FOR UPDATE SKIP LOCKED`.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.pipeline import Job

PIPELINE_KINDS = ("INGEST", "PIPELINE_STAGE", "TRAIN", "SNAPSHOT_RETIRE")
ANALYSIS_KINDS = ("INTERVENTION", "EVALUATION")


@dataclass(frozen=True)
class ClaimedJob:
    job_id: uuid.UUID
    kind: str
    payload: dict[str, Any]
    attempts: int
    max_attempts: int
    lock_key: int | None
    requested_by: uuid.UUID | None
    request_id: str | None
    started_at: datetime | None


def lock_key_for(dataset_id: uuid.UUID | str) -> int:
    """Advisory-lock key: first 8 bytes of SHA-256 of the dataset ID as a signed BIGINT [PLAN DEFAULT §7.2]."""
    digest = hashlib.sha256(str(dataset_id).encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def enqueue(
    db: Session,
    kind: str,
    payload: dict[str, Any],
    *,
    max_attempts: int,
    requested_by: uuid.UUID | None = None,
    request_id: str | None = None,
    lock_key: int | None = None,
) -> Job:
    job = Job(
        job_id=uuid.uuid4(),
        kind=kind,
        payload=payload,
        status="QUEUED",
        lock_key=lock_key,
        attempts=0,
        max_attempts=max_attempts,
        requested_by=requested_by,
        request_id=request_id,
        created_at=utcnow(),
    )
    db.add(job)
    return job


CLAIM_SQL = text(
    """
    UPDATE jobs SET status = 'RUNNING', attempts = attempts + 1, lease_owner = :worker,
           lease_expires_at = now() + make_interval(secs => :lease), started_at = coalesce(started_at, now())
    WHERE job_id = (SELECT job_id FROM jobs
                    WHERE status = 'QUEUED' AND kind = ANY(:kinds)
                    ORDER BY created_at, job_id
                    FOR UPDATE SKIP LOCKED LIMIT 1)
    RETURNING job_id, kind, payload, attempts, max_attempts, lock_key, requested_by, request_id, started_at
    """
)


def claim(conn: Connection, worker: str, kinds: tuple[str, ...], lease_seconds: int) -> ClaimedJob | None:
    row = conn.execute(CLAIM_SQL, {"worker": worker, "kinds": list(kinds), "lease": lease_seconds}).first()
    conn.commit()
    if row is None:
        return None
    return ClaimedJob(
        job_id=row.job_id,
        kind=row.kind,
        payload=dict(row.payload),
        attempts=row.attempts,
        max_attempts=row.max_attempts,
        lock_key=row.lock_key,
        requested_by=row.requested_by,
        request_id=row.request_id,
        started_at=row.started_at,
    )


def mark_succeeded(db: Session | Connection, job_id: uuid.UUID, worker: str) -> bool:
    """Terminal success, guarded: only the current lease owner of a RUNNING job may complete it."""
    result = db.execute(
        text(
            "UPDATE jobs SET status='SUCCEEDED', completed_at=now(), lease_expires_at=NULL "
            "WHERE job_id=:id AND status='RUNNING' AND lease_owner=:w"
        ),
        {"id": job_id, "w": worker},
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]


def mark_failed(
    db: Session | Connection, job_id: uuid.UUID, worker: str | None, category: str, summary: str | None
) -> bool:
    result = db.execute(
        text(
            "UPDATE jobs SET status='FAILED', completed_at=now(), lease_expires_at=NULL, failure_category=:c, "
            "error_summary=:s WHERE job_id=:id AND status='RUNNING' "
            "AND (CAST(:w AS VARCHAR) IS NULL OR lease_owner=:w)"
        ),
        {"id": job_id, "w": worker, "c": category, "s": (summary or "")[:2000] or None},
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]


def requeue(db: Session | Connection, job_id: uuid.UUID, worker: str, *, refund_attempt: bool) -> bool:
    """Return a claimed job to QUEUED (used when a dataset lock is busy; the attempt is refunded)."""
    result = db.execute(
        text(
            "UPDATE jobs SET status='QUEUED', lease_owner=NULL, lease_expires_at=NULL, "
            "attempts = attempts - :refund WHERE job_id=:id AND status='RUNNING' AND lease_owner=:w"
        ),
        {"id": job_id, "w": worker, "refund": 1 if refund_attempt else 0},
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]


def cancel(db: Session, job_id: uuid.UUID) -> bool:
    """ADMIN-only cancellation of a queued job (terminal CANCELLED)."""
    result = db.execute(
        text("UPDATE jobs SET status='CANCELLED', completed_at=now() WHERE job_id=:id AND status='QUEUED'"),
        {"id": job_id},
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]
