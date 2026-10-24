"""Per-kind wall-clock limit (SRS §7.8): exceeding it fails the job; no partial result is published."""

import time
import uuid

import pytest
from sqlalchemy import text

from mulenetx.jobs.runner import JobContext, Runner
from tests import jobutil

pytestmark = pytest.mark.integration


def test_timeout_fails_job_and_refuses_completion(clean_db: str) -> None:
    rt = jobutil.runtime(clean_db, job_timeout_snapshot_retire_seconds=1, job_heartbeat_seconds=0.3)
    [job_id] = jobutil.enqueue(rt)
    marker = uuid.uuid4()

    def slow(ctx: JobContext) -> None:
        time.sleep(2.0)
        with rt.session_factory() as session:
            session.execute(
                text(
                    "INSERT INTO audit_events (event_id, action, resource_type, outcome, timestamp) "
                    "VALUES (:id, 'test.output', 'test', 'SUCCESS', now())"
                ),
                {"id": marker},
            )
            ctx.complete(session)  # raises: the job already failed with TIMEOUT
            session.commit()

    handler = jobutil.RecordingHandler(work=slow)
    runner = Runner(rt, {"SNAPSHOT_RETIRE": handler}, worker="t")
    runner.tick()
    jobutil.wait_until(lambda: (runner.tick() or True) and jobutil.job_row(rt, job_id).status == "FAILED", 10)
    runner.running[job_id].future.result(timeout=10)
    row = jobutil.job_row(rt, job_id)
    assert row.status == "FAILED" and row.failure_category == "TIMEOUT"
    assert handler.failures == [(job_id, "TIMEOUT")]
    with rt.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM audit_events WHERE event_id=:id"), {"id": marker}).scalar() == 0
    runner.shutdown()
    rt.close()


def test_handler_exception_fails_job_with_category(clean_db: str) -> None:
    rt = jobutil.runtime(clean_db)
    [job_id] = jobutil.enqueue(rt)

    def boom(ctx: JobContext) -> None:
        raise RuntimeError("secret internal detail")

    handler = jobutil.RecordingHandler(work=boom)
    runner = Runner(rt, {"SNAPSHOT_RETIRE": handler}, worker="t")
    runner.drain(timeout=10)
    row = jobutil.job_row(rt, job_id)
    assert row.status == "FAILED" and row.failure_category == "INTERNAL"
    assert "secret internal detail" not in (row.error_summary or "")
    assert handler.failures == [(job_id, "INTERNAL")]
    runner.shutdown()
    rt.close()


def test_job_survives_backend_restart_and_is_processed(clean_db: str) -> None:
    """T07 acceptance: a committed job survives a restart of the enqueuing process."""
    api_side = jobutil.runtime(clean_db)
    [job_id] = jobutil.enqueue(api_side)
    api_side.close()  # the "backend" goes away; nothing is held in memory

    worker_side = jobutil.runtime(clean_db)
    handler = jobutil.RecordingHandler()
    runner = Runner(worker_side, {"SNAPSHOT_RETIRE": handler}, worker="fresh")
    runner.drain(timeout=10)
    assert handler.ran == [job_id]
    assert jobutil.job_row(worker_side, job_id).status == "SUCCEEDED"
    runner.shutdown()
    worker_side.close()


def test_per_kind_concurrency(clean_db: str) -> None:
    rt = jobutil.runtime(clean_db)
    jobutil.enqueue(rt, kind="SNAPSHOT_RETIRE", n=3)
    jobutil.enqueue(rt, kind="EVALUATION", n=3)
    block = jobutil.RecordingHandler(work=lambda ctx: time.sleep(0.6))
    runner = Runner(rt, {"SNAPSHOT_RETIRE": block, "EVALUATION": block}, worker="c", pipeline_slots=1, analysis_slots=2)
    runner.tick()
    kinds = sorted(r.ctx.job.kind for r in runner.running.values())
    assert kinds == ["EVALUATION", "EVALUATION", "SNAPSHOT_RETIRE"]
    runner.drain(timeout=20)
    assert len(block.ran) == 6
    runner.shutdown()
    rt.close()
