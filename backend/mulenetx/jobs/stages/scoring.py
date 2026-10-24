"""SCORING stage (SRS §11 inference, §12, §13; §7.6 rule 4)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.lineage import AnalyticsRun, GraphSnapshot, RiskLogicVersion, ScoringRun
from mulenetx.db.models.pipeline import PipelineRun
from mulenetx.jobs.runner import JobFailedError
from mulenetx.jobs.stages.base import Stage, StageContext, StageOutcome
from mulenetx.ml.registry import risk_logic_for_model
from mulenetx.risk.service import RiskService, create_scoring_run


class ScoringStage(Stage):
    name = "SCORING"

    def prerequisites_ok(self, session: Session, run: PipelineRun) -> bool:
        if run.analytics_run_id is None or run.graph_snapshot_id is None:
            return False
        analytics = session.get(AnalyticsRun, run.analytics_run_id)
        return analytics is not None and analytics.status == "SUCCEEDED"

    def delete_partial_outputs(self, ctx: StageContext) -> None:
        run = ctx.load_run()
        if run.scoring_run_id is not None:
            with ctx.runtime.engine.begin() as conn:
                conn.exec_driver_sql("SELECT purge_scoring_outputs(%s)", (run.scoring_run_id,))

    def _risk_logic(self, ctx: StageContext, run: PipelineRun, session: Session) -> RiskLogicVersion:
        name = ctx.payload.get("risk_logic_version")
        if name:
            found = session.get(RiskLogicVersion, str(name))
            if found is not None:
                return found
        if run.model_version is not None:
            linked = risk_logic_for_model(session, run.model_version)
            if linked is not None:
                return linked
        raise JobFailedError("PIPELINE_PREREQUISITE_MISSING", "no risk logic version is available for scoring")

    def execute(self, ctx: StageContext) -> StageOutcome:
        run = ctx.load_run()
        with ctx.runtime.session_factory() as session:
            snapshot = session.get(GraphSnapshot, run.graph_snapshot_id)
            analytics = session.get(AnalyticsRun, run.analytics_run_id)
            assert snapshot is not None and analytics is not None
            risk_logic = self._risk_logic(ctx, run, session)
        scoring_run_id = run.scoring_run_id or uuid.uuid4()
        create_scoring_run(
            ctx.runtime, scoring_run_id, snapshot, analytics, risk_logic.risk_logic_version, run.model_version
        )
        ctx.set_once("scoring_run_id", scoring_run_id)
        count = RiskService(ctx.runtime).score(
            scoring_run_id, snapshot, analytics, risk_logic, run.model_version, ctx.check
        )

        def finalize(session: Session) -> None:
            sr = session.get(ScoringRun, scoring_run_id, with_for_update=True)
            assert sr is not None
            sr.status = "SUCCEEDED"
            sr.accounts_scored = count
            sr.completed_at = utcnow()

        return StageOutcome(finalize=finalize)

    def on_failure(self, runtime, run, category, message):  # type: ignore[no-untyped-def]
        if run.scoring_run_id is None:
            return
        with runtime.session_factory() as session:
            sr = session.get(ScoringRun, run.scoring_run_id, with_for_update=True)
            if sr is not None and sr.status == "RUNNING":
                sr.status = "FAILED"
                session.commit()
