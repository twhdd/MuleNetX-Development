"""Job runner: claims jobs, runs handlers with per-kind concurrency, heartbeat, timeout (SRS §7.8).

Handlers run in their own transactions. The terminal SUCCEEDED update of the job row is committed in the
same transaction as the handler's final outputs (`JobContext.complete`), guarded by the lease owner, so a
job that timed out or lost its lease can never publish results.
"""

from __future__ import annotations

import logging
import os
import socket
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy.orm import Session

from mulenetx.core.errors import AppError
from mulenetx.core.logging import log_fields
from mulenetx.core.runtime import Runtime
from mulenetx.jobs import queue
from mulenetx.jobs.lease import ExpiredJob, Heartbeat, reap_expired
from mulenetx.jobs.queue import ANALYSIS_KINDS, PIPELINE_KINDS, ClaimedJob

logger = logging.getLogger("mulenetx.jobs")


class JobCancelledError(Exception):
    """Raised inside a handler when its job timed out or lost its lease."""


class LockBusyError(Exception):
    """Raised by a handler when its dataset advisory lock is held elsewhere; the job is re-queued."""


class JobFailedError(Exception):
    """A handled failure with a safe category and message (recorded on the job and its resource)."""

    def __init__(self, category: str, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


@dataclass
class JobContext:
    job: ClaimedJob
    runtime: Runtime
    worker: str
    cancelled: threading.Event = field(default_factory=threading.Event)
    completed: bool = False

    def check(self) -> None:
        if self.cancelled.is_set():
            raise JobCancelledError(str(self.job.job_id))

    def complete(self, session: Session) -> None:
        """Mark the job SUCCEEDED inside the caller's transaction (commit is the caller's)."""
        self.check()
        if not queue.mark_succeeded(session, self.job.job_id, self.worker):
            raise JobCancelledError(str(self.job.job_id))
        self.completed = True


class Handler(Protocol):
    def run(self, ctx: JobContext) -> None: ...

    def on_failure(
        self, runtime: Runtime, job_id: uuid.UUID, payload: dict[str, object], category: str, message: str
    ) -> None: ...


def worker_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def failure_category(exc: BaseException) -> str:
    if isinstance(exc, JobFailedError):
        return exc.category
    if isinstance(exc, AppError):
        if exc.code in ("GRAPH_UNAVAILABLE", "DB_UNAVAILABLE", "MODEL_UNAVAILABLE"):
            return "DEPENDENCY_UNAVAILABLE"
        if exc.code == "LIMIT_EXCEEDED":
            return "LIMIT_EXCEEDED"
    return "INTERNAL"


def safe_message(exc: BaseException) -> str:
    if isinstance(exc, JobFailedError):
        return exc.message
    if isinstance(exc, AppError):
        return exc.message
    return "internal error; see worker logs for the job id"


@dataclass
class _Running:
    ctx: JobContext
    future: Future[None]
    heartbeat: Heartbeat
    started: float
    timeout: float
    slot: str


class Runner:
    def __init__(
        self,
        runtime: Runtime,
        handlers: dict[str, Handler],
        *,
        worker: str | None = None,
        pipeline_slots: int | None = None,
        analysis_slots: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        s = runtime.settings
        self.runtime = runtime
        self.handlers = handlers
        self.worker = worker or worker_identity()
        self.slots = {
            "pipeline": pipeline_slots if pipeline_slots is not None else s.worker_pipeline_slots,
            "analysis": analysis_slots if analysis_slots is not None else s.worker_analysis_slots,
        }
        self.pool = ThreadPoolExecutor(max_workers=sum(self.slots.values()), thread_name_prefix="job")
        self.running: dict[uuid.UUID, _Running] = {}
        self.clock = clock
        self.stopping = threading.Event()

    # ── loop ───────────────────────────────────────────────────────────────

    def run_forever(self) -> None:
        log_fields(logger, logging.INFO, "worker started", worker=self.worker, slots=self.slots)
        while not self.stopping.is_set():
            self.tick()
            self.stopping.wait(self.runtime.settings.worker_poll_seconds)
        self.shutdown()

    def tick(self) -> int:
        """One loop iteration: reap, enforce timeouts, collect finished, claim. Returns jobs claimed."""
        reap_expired(self.runtime.engine, self._on_lease_failure)
        self._enforce_timeouts()
        self._collect()
        claimed = 0
        for slot, all_kinds in (("pipeline", PIPELINE_KINDS), ("analysis", ANALYSIS_KINDS)):
            kinds = tuple(k for k in all_kinds if k in self.handlers)
            while kinds and self._free(slot) > 0:
                with self.runtime.engine.connect() as conn:
                    job = queue.claim(conn, self.worker, kinds, self.runtime.settings.job_lease_seconds)
                if job is None:
                    break
                self._start(job, slot)
                claimed += 1
        return claimed

    def drain(self, timeout: float = 60.0) -> None:
        """Run ticks until no job is running or queued for this runner's kinds (tests and CLI)."""
        deadline = self.clock() + timeout
        while self.clock() < deadline:
            claimed = self.tick()
            if not self.running and claimed == 0:
                return
            time.sleep(0.05)
        raise TimeoutError("runner did not drain")

    def shutdown(self) -> None:
        self.stopping.set()
        for r in self.running.values():
            r.heartbeat.stop()
        self.pool.shutdown(wait=False, cancel_futures=True)

    # ── internals ──────────────────────────────────────────────────────────

    def _free(self, slot: str) -> int:
        return self.slots[slot] - sum(1 for r in self.running.values() if r.slot == slot)

    def _start(self, job: ClaimedJob, slot: str) -> None:
        s = self.runtime.settings
        ctx = JobContext(job=job, runtime=self.runtime, worker=self.worker)
        hb = Heartbeat(self.runtime.engine, job.job_id, self.worker, s.job_lease_seconds, s.job_heartbeat_seconds)
        hb.start()
        log_fields(
            logger,
            logging.INFO,
            "job attempt started",
            job_id=str(job.job_id),
            kind=job.kind,
            attempt=job.attempts,
            stage=job.payload.get("stage"),
        )
        future = self.pool.submit(self._execute, ctx, hb)
        self.running[job.job_id] = _Running(ctx, future, hb, self.clock(), float(s.job_timeout_seconds(job.kind)), slot)

    def _execute(self, ctx: JobContext, hb: Heartbeat) -> None:
        job = ctx.job
        handler = self.handlers[job.kind]
        try:
            handler.run(ctx)
            if not ctx.completed:
                with self.runtime.session_factory() as session:
                    ctx.complete(session)
                    session.commit()
            log_fields(
                logger,
                logging.INFO,
                "job succeeded",
                job_id=str(job.job_id),
                kind=job.kind,
                attempt=job.attempts,
                stage=job.payload.get("stage"),
            )
        except JobCancelledError:
            log_fields(
                logger,
                logging.WARNING,
                "job cancelled (timeout or lease lost)",
                job_id=str(job.job_id),
                kind=job.kind,
                attempt=job.attempts,
            )
        except LockBusyError:
            with self.runtime.engine.begin() as conn:
                queue.requeue(conn, job.job_id, self.worker, refund_attempt=True)
            log_fields(logger, logging.INFO, "job requeued: dataset lock busy", job_id=str(job.job_id), kind=job.kind)
        except Exception as exc:  # noqa: BLE001 - every failure is recorded on the job
            category, message = failure_category(exc), safe_message(exc)
            logger.error(
                "job failed",
                exc_info=not isinstance(exc, JobFailedError | AppError),
                extra={
                    "fields": {
                        "job_id": str(job.job_id),
                        "kind": job.kind,
                        "attempt": job.attempts,
                        "failure_category": category,
                    }
                },
            )
            with self.runtime.engine.begin() as conn:
                owned = queue.mark_failed(conn, job.job_id, self.worker, category, message)
            if owned:
                handler.on_failure(self.runtime, job.job_id, job.payload, category, message)
        finally:
            hb.stop()

    def _collect(self) -> None:
        for job_id in [j for j, r in self.running.items() if r.future.done()]:
            r = self.running.pop(job_id)
            if r.heartbeat.lost.is_set():
                r.ctx.cancelled.set()

    def _enforce_timeouts(self) -> None:
        now = self.clock()
        for r in list(self.running.values()):
            if r.heartbeat.lost.is_set():
                r.ctx.cancelled.set()
            if not r.future.done() and now - r.started > r.timeout and not r.ctx.cancelled.is_set():
                r.ctx.cancelled.set()
                job = r.ctx.job
                with self.runtime.engine.begin() as conn:
                    owned = queue.mark_failed(
                        conn, job.job_id, self.worker, "TIMEOUT", f"job exceeded its {int(r.timeout)} s limit"
                    )
                r.heartbeat.stop()
                log_fields(
                    logger,
                    logging.WARNING,
                    "job timed out",
                    job_id=str(job.job_id),
                    kind=job.kind,
                    attempt=job.attempts,
                )
                if owned:
                    self.handlers[job.kind].on_failure(
                        self.runtime, job.job_id, job.payload, "TIMEOUT", "the job exceeded its time limit"
                    )

    def _on_lease_failure(self, expired: ExpiredJob) -> None:
        handler = self.handlers.get(expired.kind)
        if handler is not None:
            handler.on_failure(
                self.runtime,
                expired.job_id,
                expired.payload,
                "LEASE_EXPIRED",
                "the worker stopped renewing the job lease",
            )
