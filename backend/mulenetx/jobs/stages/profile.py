"""PROFILING stage (SRS §7.9)."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.datasets import DatasetProfile
from mulenetx.db.models.pipeline import IngestionRun, PipelineRun
from mulenetx.jobs.stages.base import Stage, StageContext, StageOutcome
from mulenetx.profiling.service import PROFILE_VERSION, compute_profile


class ProfileStage(Stage):
    name = "PROFILING"

    def prerequisites_ok(self, session: Session, run: PipelineRun) -> bool:
        if run.ingestion_run_id is None:
            return False
        ingestion = session.get(IngestionRun, run.ingestion_run_id)
        return ingestion is not None and ingestion.status == "SUCCEEDED"

    def execute(self, ctx: StageContext) -> StageOutcome:
        with ctx.runtime.session_factory() as session:
            if session.get(DatasetProfile, ctx.dataset_id) is not None:
                return StageOutcome()  # the profile is immutable and computed once per dataset
            run = ctx.run(session)
            ingestion = session.get(IngestionRun, run.ingestion_run_id)
            assert ingestion is not None
            summary = {
                "records_seen": ingestion.records_seen,
                "records_accepted": ingestion.records_accepted,
                "records_rejected": ingestion.records_rejected,
                "records_duplicate": ingestion.records_duplicate,
                "rejection_summary": ingestion.rejection_summary,
            }
        metrics = compute_profile(
            ctx.runtime.engine, ctx.dataset_id, summary, ctx.runtime.settings.analytic_max_expansions
        )
        with ctx.runtime.session_factory() as session:
            session.execute(
                insert(DatasetProfile)
                .values(
                    dataset_id=ctx.dataset_id, profile_version=PROFILE_VERSION, metrics=metrics, created_at=utcnow()
                )
                .on_conflict_do_nothing()
            )
            session.commit()
        return StageOutcome()
