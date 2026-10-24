"""GRAPH_BUILDING stage (SRS §6.8): build and validate the OPERATIONAL snapshot (data_cutoff = the
dataset's maximum transaction timestamp)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mulenetx.core.runtime import Runtime
from mulenetx.db.models.canonical import Transaction
from mulenetx.db.models.pipeline import IngestionRun, PipelineRun
from mulenetx.graph.service import GraphService, GraphValidationMismatchError
from mulenetx.jobs.runner import JobFailedError
from mulenetx.jobs.stages.base import Stage, StageContext, StageOutcome


class GraphBuildStage(Stage):
    name = "GRAPH_BUILDING"

    def prerequisites_ok(self, session: Session, run: PipelineRun) -> bool:
        if run.ingestion_run_id is None:
            return False
        ingestion = session.get(IngestionRun, run.ingestion_run_id)
        return ingestion is not None and ingestion.status == "SUCCEEDED"

    def execute(self, ctx: StageContext) -> StageOutcome:
        run = ctx.load_run()
        with ctx.runtime.session_factory() as session:
            bound = session.execute(
                select(func.max(Transaction.timestamp)).where(Transaction.dataset_id == ctx.dataset_id)
            ).scalar_one()
        if bound is None:
            raise JobFailedError("PIPELINE_PREREQUISITE_MISSING", "the dataset has no accepted transactions")
        assert run.ingestion_run_id is not None
        service = GraphService(ctx.runtime)
        if run.graph_snapshot_id is not None:
            snapshot_id = run.graph_snapshot_id
        else:
            snap = service.prepare_snapshot(ctx.dataset_id, run.ingestion_run_id, "OPERATIONAL", bound)
            assert snap is not None
            snapshot_id = snap.graph_snapshot_id
        ctx.set_once("graph_snapshot_id", snapshot_id)
        try:
            service.build_and_validate(snapshot_id, ctx.check)
        except GraphValidationMismatchError as exc:
            raise JobFailedError("GRAPH_VALIDATION_MISMATCH", f"graph validation mismatch: {exc}") from exc
        return StageOutcome()

    def on_failure(self, runtime: Runtime, run: PipelineRun, category: str, message: str) -> None:
        if run.graph_snapshot_id is not None:
            GraphService(runtime).mark_failed(run.graph_snapshot_id)
