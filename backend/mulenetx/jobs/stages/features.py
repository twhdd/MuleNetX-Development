"""FEATURES_RUNNING stage (SRS §10): one vector per account of the dataset at T = the operational
snapshot's data_cutoff."""

from __future__ import annotations

from sqlalchemy.orm import Session

from mulenetx.db.models.lineage import AnalyticsRun, GraphSnapshot
from mulenetx.db.models.pipeline import PipelineRun
from mulenetx.features.service import FeatureService, GraphContext
from mulenetx.jobs.stages.base import Stage, StageContext, StageOutcome


class FeaturesStage(Stage):
    name = "FEATURES_RUNNING"

    def prerequisites_ok(self, session: Session, run: PipelineRun) -> bool:
        if run.analytics_run_id is None:
            return False
        analytics = session.get(AnalyticsRun, run.analytics_run_id)
        return analytics is not None and analytics.status == "SUCCEEDED"

    def execute(self, ctx: StageContext) -> StageOutcome:
        run = ctx.load_run()
        with ctx.runtime.session_factory() as session:
            snapshot = session.get(GraphSnapshot, run.graph_snapshot_id)
            analytics = session.get(AnalyticsRun, run.analytics_run_id)
            assert snapshot is not None and analytics is not None
        fsid = FeatureService(ctx.runtime).generate(
            ctx.dataset_id, snapshot.data_cutoff, GraphContext(snapshot, analytics), check=ctx.check
        )
        return StageOutcome(next_payload={"feature_snapshot_id": str(fsid)})
