"""Job handler that executes one pipeline stage per job (PLAN §7.3).

The run enters the stage's running state when the job starts; when the stage succeeds, one transaction
writes the stage's final outputs, moves the run to the stage's done state, enqueues the next stage job and
marks the job SUCCEEDED.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from mulenetx.audit.service import AuditService
from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.pipeline import PipelineRun
from mulenetx.jobs import queue
from mulenetx.jobs.locks import dataset_lock
from mulenetx.jobs.pipeline_state import STAGES, TERMINAL, advance
from mulenetx.jobs.runner import JobContext, JobFailedError
from mulenetx.jobs.stages import REGISTRY
from mulenetx.jobs.stages.base import StageContext, StageOutcome
from mulenetx.jobs.stages.training import compatible_model

logger = logging.getLogger("mulenetx.pipeline")

SET_ONCE_COLUMNS = ("ingestion_run_id", "graph_snapshot_id", "analytics_run_id", "scoring_run_id", "model_version")

# done state -> next running state (FEATURES_READY is decided by §7.6 rule 3)
NEXT: dict[str, str] = {
    "INGESTED": "PROFILING",
    "PROFILED": "GRAPH_BUILDING",
    "GRAPH_READY": "ANALYTICS_RUNNING",
    "ANALYTICS_READY": "FEATURES_RUNNING",
    "MODEL_READY": "SCORING",
    "SCORED": "RING_ANALYSIS",
}


def enqueue_stage(
    session: Session,
    run: PipelineRun,
    stage_state: str,
    settings_max_attempts: int,
    payload: dict[str, Any] | None = None,
    requested_by: uuid.UUID | None = None,
    request_id: str | None = None,
) -> None:
    stage = REGISTRY[stage_state]
    queue.enqueue(
        session,
        stage.kind,
        {
            "pipeline_run_id": str(run.pipeline_run_id),
            "dataset_id": str(run.dataset_id),
            "stage": stage_state,
            **(payload or {}),
        },
        max_attempts=settings_max_attempts,
        requested_by=requested_by,
        request_id=request_id,
        lock_key=queue.lock_key_for(run.dataset_id),
    )


class PipelineStageHandler:
    def run(self, ctx: JobContext) -> None:
        payload = ctx.job.payload
        stage = REGISTRY[str(payload["stage"])]
        run_id = uuid.UUID(str(payload["pipeline_run_id"]))
        dataset_id = uuid.UUID(str(payload["dataset_id"]))
        rt = ctx.runtime
        before, _after = STAGES[stage.name]

        with dataset_lock(rt.engine, ctx.job.lock_key or queue.lock_key_for(dataset_id)):
            with rt.session_factory() as session:
                run = session.get(PipelineRun, run_id, with_for_update=True)
                if run is None:
                    raise JobFailedError("INTERNAL", "pipeline run not found")
                if run.current_state != stage.name:
                    if run.current_state in TERMINAL:
                        raise JobFailedError("INTERNAL", f"pipeline run is {run.current_state}")
                    run.current_state = advance(run.current_state, stage.name)
                    run.updated_at = utcnow()
                if not stage.prerequisites_ok(session, run):
                    session.commit()
                    raise JobFailedError("PIPELINE_PREREQUISITE_MISSING", f"prerequisites of {stage.name} are missing")
                session.commit()

            sctx = StageContext(runtime=rt, job=ctx, pipeline_run_id=run_id, dataset_id=dataset_id, payload=payload)
            stage.delete_partial_outputs(sctx)
            ctx.check()
            outcome = stage.execute(sctx)
            ctx.check()
            self._finish(ctx, sctx, stage.name, outcome)

    def _finish(self, ctx: JobContext, sctx: StageContext, stage_state: str, outcome: StageOutcome) -> None:
        rt = ctx.runtime
        _before, after = STAGES[stage_state]
        with rt.session_factory() as session:
            run = session.get(PipelineRun, sctx.pipeline_run_id, with_for_update=True)
            assert run is not None
            for column, value in outcome.run_updates.items():
                if column in SET_ONCE_COLUMNS and getattr(run, column) is not None:
                    continue
                setattr(run, column, value)
            session.flush()
            if outcome.finalize is not None:
                outcome.finalize(session)
            now = utcnow()
            run.current_state = advance(run.current_state, after)
            run.updated_at = now
            if after == "READY":
                run.completed_at = now
            next_state = self._next(session, run)
            if next_state is not None:
                enqueue_stage(
                    session,
                    run,
                    next_state,
                    rt.settings.job_max_attempts,
                    outcome.next_payload,
                    ctx.job.requested_by,
                    ctx.job.request_id,
                )
            ctx.complete(session)
            session.commit()

    @staticmethod
    def _next(session: Session, run: PipelineRun) -> str | None:
        if run.current_state == "FEATURES_READY":
            model = compatible_model(session, run)
            if model is not None:
                if run.model_version is None:
                    run.model_version = model
                return "SCORING"
            return "TRAINING"
        return NEXT.get(run.current_state)

    def on_failure(
        self, runtime: Runtime, job_id: uuid.UUID, payload: dict[str, object], category: str, message: str
    ) -> None:
        stage_state = str(payload.get("stage"))
        run_id = uuid.UUID(str(payload["pipeline_run_id"]))
        with runtime.session_factory() as session:
            run = session.get(PipelineRun, run_id, with_for_update=True)
            if run is None or run.current_state in TERMINAL:
                return
            run.current_state = advance(run.current_state, "FAILED")
            run.failure_stage = stage_state
            run.failure_category = category[:50]
            run.safe_failure_message = message[:2000]
            run.resumable_from = stage_state
            run.updated_at = utcnow()
            session.add(
                AuditService.build(
                    "pipeline.stage_failed",
                    "pipeline_run",
                    "FAILED",
                    resource_id=str(run_id),
                    metadata={"stage": stage_state, "failure_category": category, "job_id": str(job_id)},
                )
            )
            session.commit()
            stage = REGISTRY.get(stage_state)
            if stage is not None:
                stage.on_failure(runtime, run, category, message)
