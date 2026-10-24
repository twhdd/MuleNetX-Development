"""Lease heartbeat and the lease-expiry reaper (SRS §7.8 points 2 and 4)."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import Engine, text

logger = logging.getLogger("mulenetx.jobs")


class Heartbeat(threading.Thread):
    """Renews the lease of one RUNNING job every `interval` seconds; sets `lost` when renewal fails."""

    def __init__(self, engine: Engine, job_id: uuid.UUID, worker: str, lease_seconds: int, interval: float) -> None:
        super().__init__(name=f"heartbeat-{job_id}", daemon=True)
        self.engine = engine
        self.job_id = job_id
        self.worker = worker
        self.lease_seconds = lease_seconds
        self.interval = interval
        self.stopped = threading.Event()
        self.lost = threading.Event()

    def run(self) -> None:
        while not self.stopped.wait(self.interval):
            try:
                with self.engine.begin() as conn:
                    result = conn.execute(
                        text(
                            "UPDATE jobs SET lease_expires_at = now() + make_interval(secs => :lease) "
                            "WHERE job_id = :id AND status = 'RUNNING' AND lease_owner = :w"
                        ),
                        {"lease": self.lease_seconds, "id": self.job_id, "w": self.worker},
                    )
                if not result.rowcount:
                    self.lost.set()
                    return
            except Exception:  # noqa: BLE001 - a missed beat is tolerated; expiry is the recovery mechanism
                logger.warning("lease heartbeat failed for job %s", self.job_id)

    def stop(self) -> None:
        self.stopped.set()


@dataclass(frozen=True)
class ExpiredJob:
    job_id: uuid.UUID
    kind: str
    payload: dict[str, object]
    attempts: int
    max_attempts: int
    requeued: bool


FailureHook = Callable[[ExpiredJob], None]


def reap_expired(engine: Engine, on_final_failure: FailureHook | None = None) -> list[ExpiredJob]:
    """Return expired RUNNING jobs to QUEUED, or FAIL them with LEASE_EXPIRED after `max_attempts`."""
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT job_id, kind, payload, attempts, max_attempts FROM jobs "
                "WHERE status = 'RUNNING' AND lease_expires_at < now() FOR UPDATE SKIP LOCKED"
            )
        ).all()
        out: list[ExpiredJob] = []
        for r in rows:
            if r.attempts < r.max_attempts:
                conn.execute(
                    text(
                        "UPDATE jobs SET status='QUEUED', lease_owner=NULL, lease_expires_at=NULL, "
                        "failure_category='LEASE_EXPIRED', error_summary='lease expired; returned to queue' "
                        "WHERE job_id=:id"
                    ),
                    {"id": r.job_id},
                )
                out.append(ExpiredJob(r.job_id, r.kind, dict(r.payload), r.attempts, r.max_attempts, True))
            else:
                conn.execute(
                    text(
                        "UPDATE jobs SET status='FAILED', completed_at=now(), lease_expires_at=NULL, "
                        "failure_category='LEASE_EXPIRED', error_summary='lease expired after the last attempt' "
                        "WHERE job_id=:id"
                    ),
                    {"id": r.job_id},
                )
                out.append(ExpiredJob(r.job_id, r.kind, dict(r.payload), r.attempts, r.max_attempts, False))
    for job in out:
        logger.warning(
            "lease expired",
            extra={
                "fields": {
                    "job_id": str(job.job_id),
                    "kind": job.kind,
                    "attempt": job.attempts,
                    "requeued": job.requeued,
                }
            },
        )
        if not job.requeued and on_final_failure is not None:
            on_final_failure(job)
    return out
