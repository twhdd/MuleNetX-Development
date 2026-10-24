"""INGESTING stage (SRS §7.2).

With a staged upload in the job payload, the stage runs the PaySim ingestion. Without one (POST
/pipeline-runs on an already ingested dataset), it links the dataset's latest successful ingestion run.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from mulenetx.core.runtime import Runtime
from mulenetx.db.models.pipeline import IngestionRun, PipelineRun
from mulenetx.jobs.runner import JobFailedError
from mulenetx.jobs.stages.base import Stage, StageContext, StageOutcome


def latest_succeeded_ingestion(session: Session, dataset_id: object) -> IngestionRun | None:
    return session.execute(
        select(IngestionRun)
        .where(IngestionRun.dataset_id == dataset_id, IngestionRun.status == "SUCCEEDED")
        .order_by(IngestionRun.started_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _service(rt: Runtime):  # type: ignore[no-untyped-def]
    from mulenetx.audit.service import AuditService
    from mulenetx.ingestion.service import IngestionService
    from mulenetx.jobs.service import JobService

    audit = AuditService(rt.session_factory)
    return IngestionService(rt.settings, audit, JobService(rt.settings, audit))


class IngestStage(Stage):
    name = "INGESTING"
    kind = "INGEST"

    def execute(self, ctx: StageContext) -> StageOutcome:
        staged = ctx.payload.get("staged_path")
        ingestion_id = ctx.payload.get("ingestion_run_id")
        if staged and ingestion_id:
            path = Path(str(staged))
            if not path.is_file():
                raise JobFailedError("PIPELINE_PREREQUISITE_MISSING", "the staged upload is no longer available")
            outcome: StageOutcome = _service(ctx.runtime).execute(ctx, uuid.UUID(str(ingestion_id)), path)
            return outcome
        with ctx.runtime.session_factory() as session:
            run = ctx.run(session)
            if run.ingestion_run_id is not None:
                ingestion = session.get(IngestionRun, run.ingestion_run_id)
                if ingestion is not None and ingestion.status == "SUCCEEDED":
                    return StageOutcome()
            existing = latest_succeeded_ingestion(session, ctx.dataset_id)
        if existing is None:
            raise JobFailedError("PIPELINE_PREREQUISITE_MISSING", "the dataset has no successful ingestion run")
        return StageOutcome(run_updates={"ingestion_run_id": existing.ingestion_run_id})

    def on_failure(self, runtime: Runtime, run: PipelineRun, category: str, message: str) -> None:
        if run.ingestion_run_id is not None:
            _service(runtime).on_failure(runtime.session_factory, run.ingestion_run_id, message)
