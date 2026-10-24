"""Lease expiry is the only recovery mechanism (SRS §7.8 point 4)."""

import time

import pytest
from sqlalchemy import text

from mulenetx.jobs import queue
from mulenetx.jobs.lease import reap_expired
from mulenetx.jobs.runner import Runner
from tests import jobutil

pytestmark = pytest.mark.integration


def _expire(rt, job_id) -> None:
    with rt.engine.begin() as conn:
        conn.execute(
            text("UPDATE jobs SET lease_expires_at = now() - interval '1 second' WHERE job_id=:id"), {"id": job_id}
        )


def test_dead_worker_job_requeued_then_failed(clean_db: str) -> None:
    rt = jobutil.runtime(clean_db)
    [job_id] = jobutil.enqueue(rt, max_attempts=2)
    finals = []
    # attempt 1: the "worker" claims and dies (no heartbeat)
    with rt.engine.connect() as conn:
        assert queue.claim(conn, "dead-1", ("SNAPSHOT_RETIRE",), 60) is not None
    _expire(rt, job_id)
    out = reap_expired(rt.engine, finals.append)
    assert [o.requeued for o in out] == [True]
    row = jobutil.job_row(rt, job_id)
    assert (row.status, row.attempts, row.failure_category) == ("QUEUED", 1, "LEASE_EXPIRED")
    # attempt 2: dies again → FAILED LEASE_EXPIRED; final-failure hook called once
    with rt.engine.connect() as conn:
        assert queue.claim(conn, "dead-2", ("SNAPSHOT_RETIRE",), 60) is not None
    _expire(rt, job_id)
    reap_expired(rt.engine, finals.append)
    row = jobutil.job_row(rt, job_id)
    assert (row.status, row.attempts, row.failure_category) == ("FAILED", 2, "LEASE_EXPIRED")
    assert [f.job_id for f in finals] == [job_id]
    rt.close()


def test_killed_handler_thread_job_recovered_by_another_worker(clean_db: str) -> None:
    """A runner whose handler hangs and whose heartbeat stops (simulated crash) loses the job; after
    lease expiry a second runner processes it."""
    rt = jobutil.runtime(clean_db, job_lease_seconds=1)
    [job_id] = jobutil.enqueue(rt)
    hang = jobutil.RecordingHandler(work=lambda ctx: time.sleep(3))
    crashed = Runner(rt, {"SNAPSHOT_RETIRE": hang}, worker="crashed")
    crashed.tick()
    running = crashed.running[job_id]
    running.heartbeat.stop()  # the process "dies": no more lease renewals
    jobutil.wait_until(lambda: jobutil.job_row(rt, job_id).lease_expires_at is not None, 5)
    time.sleep(1.5)
    ok = jobutil.RecordingHandler()
    survivor = Runner(rt, {"SNAPSHOT_RETIRE": ok}, worker="survivor")
    survivor.drain(timeout=20)
    row = jobutil.job_row(rt, job_id)
    assert row.status == "SUCCEEDED" and row.attempts == 2 and row.lease_owner == "survivor"
    assert ok.ran == [job_id]
    # the crashed runner's late completion is refused (lease owner changed)
    crashed.running[job_id].future.result(timeout=10)
    assert jobutil.job_row(rt, job_id).lease_owner == "survivor"
    crashed.shutdown()
    survivor.shutdown()
    rt.close()


def test_heartbeat_keeps_long_job_alive(clean_db: str) -> None:
    rt = jobutil.runtime(clean_db, job_lease_seconds=1, job_heartbeat_seconds=0.3)
    [job_id] = jobutil.enqueue(rt)
    slow = jobutil.RecordingHandler(work=lambda ctx: time.sleep(2.5))
    runner = Runner(rt, {"SNAPSHOT_RETIRE": slow}, worker="slow")
    runner.drain(timeout=20)
    row = jobutil.job_row(rt, job_id)
    assert row.status == "SUCCEEDED" and row.attempts == 1
    runner.shutdown()
    rt.close()
