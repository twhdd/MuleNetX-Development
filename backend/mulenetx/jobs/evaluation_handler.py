"""EVALUATION job (SRS §28.7, §7.8): computes every level and writes the metrics in one transaction."""

from __future__ import annotations

import uuid

from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.evaluation import EvaluationMetric, EvaluationRun
from mulenetx.evaluation.service import EvaluationFailedError, compute
from mulenetx.jobs.runner import JobContext, JobFailedError


class EvaluationHandler:
    def run(self, ctx: JobContext) -> None:
        run_id = uuid.UUID(str(ctx.job.payload["evaluation_run_id"]))
        rt = ctx.runtime
        with rt.session_factory() as db:
            run = db.get(EvaluationRun, run_id, with_for_update=True)
            if run is None:
                raise JobFailedError("INTERNAL", "evaluation run not found")
            if run.status == "QUEUED":
                run.status = "RUNNING"
                db.commit()
        with rt.session_factory() as db:
            run = db.get(EvaluationRun, run_id)
            assert run is not None
            try:
                rows = compute(rt.engine, rt.settings, db, run)
            except EvaluationFailedError as exc:
                raise JobFailedError("PIPELINE_PREREQUISITE_MISSING", str(exc)) from exc
            db.rollback()
        ctx.check()
        with rt.session_factory() as db:
            run = db.get(EvaluationRun, run_id, with_for_update=True)
            assert run is not None
            db.add_all(
                EvaluationMetric(
                    evaluation_run_id=run_id,
                    level=r.level,
                    metric=r.metric,
                    value=r.value,
                    sample_count=r.sample_count,
                    availability=r.availability,
                    details=r.details,
                )
                for r in rows
            )
            run.status = "COMPLETED"
            run.completed_at = utcnow()
            ctx.complete(db)
            db.commit()

    def on_failure(
        self, runtime: Runtime, job_id: uuid.UUID, payload: dict[str, object], category: str, message: str
    ) -> None:
        run_id = uuid.UUID(str(payload["evaluation_run_id"]))
        with runtime.session_factory() as db:
            run = db.get(EvaluationRun, run_id, with_for_update=True)
            if run is not None and run.status in ("QUEUED", "RUNNING"):
                run.status = "FAILED"
                run.completed_at = utcnow()
                db.commit()
