"""ANALYTICS_RUNNING stage (SRS §8; motifs §15.9 are added in T31)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from mulenetx.analytics.service import AnalyticsService
from mulenetx.db.models.lineage import AnalyticsRun, GraphSnapshot
from mulenetx.db.models.pipeline import PipelineRun
from mulenetx.jobs.stages.base import Stage, StageContext, StageOutcome


class AnalyticsStage(Stage):
    name = "ANALYTICS_RUNNING"

    def prerequisites_ok(self, session: Session, run: PipelineRun) -> bool:
        if run.graph_snapshot_id is None:
            return False
        snapshot = session.get(GraphSnapshot, run.graph_snapshot_id)
        return snapshot is not None and snapshot.status == "READY"

    def execute(self, ctx: StageContext) -> StageOutcome:
        run = ctx.load_run()
        if run.analytics_run_id is not None:
            with ctx.runtime.session_factory() as session:
                existing = session.get(AnalyticsRun, run.analytics_run_id)
                if existing is not None and existing.status == "SUCCEEDED":
                    return StageOutcome()
        with ctx.runtime.session_factory() as session:
            snap = session.get(GraphSnapshot, run.graph_snapshot_id)
            assert snap is not None
            snapshot_id, dataset_id, cutoff = snap.graph_snapshot_id, snap.dataset_id, snap.data_cutoff
        result = AnalyticsService(ctx.runtime).run(snapshot_id, dataset_id, cutoff)
        ctx.check()
        ctx.set_once("analytics_run_id", result.analytics_run_id)
        return StageOutcome()
