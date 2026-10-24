"""Helpers for job-queue tests."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from sqlalchemy import text

from mulenetx.core.runtime import Runtime
from mulenetx.jobs import queue
from mulenetx.jobs.runner import JobContext
from tests.conftest import make_settings


def runtime(dsn: str, **overrides: Any) -> Runtime:
    values = {"job_lease_seconds": 2, "job_heartbeat_seconds": 1, "worker_poll_seconds": 0.05, **overrides}
    return Runtime(make_settings(postgres_dsn=dsn, **values))


def enqueue(rt: Runtime, kind: str = "SNAPSHOT_RETIRE", n: int = 1, max_attempts: int = 3) -> list[uuid.UUID]:
    ids: list[uuid.UUID] = []
    with rt.session_factory() as db:
        for i in range(n):
            ids.append(queue.enqueue(db, kind, {"n": i}, max_attempts=max_attempts).job_id)
        db.commit()
    return ids


def job_row(rt: Runtime, job_id: uuid.UUID) -> Any:
    with rt.engine.connect() as conn:
        return conn.execute(text("SELECT * FROM jobs WHERE job_id=:id"), {"id": job_id}).one()


class RecordingHandler:
    def __init__(self, work: Any = None) -> None:
        self.work = work
        self.ran: list[uuid.UUID] = []
        self.failures: list[tuple[uuid.UUID, str]] = []
        self.lock = threading.Lock()

    def run(self, ctx: JobContext) -> None:
        if self.work is not None:
            self.work(ctx)
        with self.lock:
            self.ran.append(ctx.job.job_id)

    def on_failure(
        self, runtime: Runtime, job_id: uuid.UUID, payload: dict[str, object], category: str, message: str
    ) -> None:
        with self.lock:
            self.failures.append((job_id, category))


def wait_until(predicate: Any, timeout: float = 10.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("condition not reached")
