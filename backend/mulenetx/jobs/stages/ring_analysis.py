"""RING_ANALYSIS stage (SRS §9, §9A) followed by activation (§6.9) in the same final transaction."""

from __future__ import annotations

from sqlalchemy.orm import Session

from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.lineage import ScoringRun
from mulenetx.db.models.pipeline import PipelineRun
from mulenetx.jobs.stages.activate import activate
from mulenetx.jobs.stages.base import Stage, StageContext, StageOutcome
from mulenetx.rings.service import RingIntelligenceService


class RingAnalysisStage(Stage):
    name = "RING_ANALYSIS"

    def prerequisites_ok(self, session: Session, run: PipelineRun) -> bool:
        if run.scoring_run_id is None or run.analytics_run_id is None or run.graph_snapshot_id is None:
            return False
        scoring = session.get(ScoringRun, run.scoring_run_id)
        return scoring is not None and scoring.status == "SUCCEEDED"

    def execute(self, ctx: StageContext) -> StageOutcome:
        max_attempts = ctx.runtime.settings.job_max_attempts
        run = ctx.load_run()
        assert run.graph_snapshot_id and run.analytics_run_id and run.scoring_run_id
        service = RingIntelligenceService(ctx.runtime)
        analysis = service.analyze(run.dataset_id, run.graph_snapshot_id, run.analytics_run_id, run.scoring_run_id)
        ctx.check()

        def finalize(session: Session) -> None:
            service.persist(session, analysis, utcnow())
            activate(session, ctx.run(session), max_attempts)

        return StageOutcome(finalize=finalize)
