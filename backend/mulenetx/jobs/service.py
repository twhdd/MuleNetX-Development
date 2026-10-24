"""JobService: pipeline runs, retry, metrics, active context (SRS §7.6–§7.8, §24.2, §6.9)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from mulenetx.audit.service import AuditService
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.config import Settings
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import PageRequest
from mulenetx.core.timeutil import isoformat_utc, utcnow
from mulenetx.db.models.datasets import Dataset
from mulenetx.db.models.lineage import ActiveContext, GraphSnapshot, ModelVersion
from mulenetx.db.models.pipeline import IngestionRun, PipelineRun
from mulenetx.jobs.pipeline_handler import enqueue_stage
from mulenetx.jobs.pipeline_state import RUNNING_STATES, TERMINAL, advance
from mulenetx.jobs.stages import REGISTRY
from mulenetx.jobs.stages.ingest import latest_succeeded_ingestion

STAGE_METRIC = {
    "INGESTING": "ingestion_duration",
    "PROFILING": "profiling_duration",
    "GRAPH_BUILDING": "graph_build_duration",
    "ANALYTICS_RUNNING": "analytics_duration",
    "FEATURES_RUNNING": "feature_generation_duration",
    "TRAINING": "training_duration",
    "SCORING": "scoring_duration",
    "RING_ANALYSIS": "ring_analysis_duration",
}


def _iso(value: Any) -> str | None:
    return None if value is None else isoformat_utc(value)


def _str(value: Any) -> str | None:
    return None if value is None else str(value)


def run_view(run: PipelineRun, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "pipeline_run_id": str(run.pipeline_run_id),
        "dataset_id": str(run.dataset_id),
        "ingestion_run_id": _str(run.ingestion_run_id),
        "current_state": run.current_state,
        "graph_snapshot_id": _str(run.graph_snapshot_id),
        "analytics_run_id": _str(run.analytics_run_id),
        "scoring_run_id": _str(run.scoring_run_id),
        "model_version": run.model_version,
        "started_at": _iso(run.started_at),
        "updated_at": _iso(run.updated_at),
        "completed_at": _iso(run.completed_at),
        "failure_stage": run.failure_stage,
        "failure_category": run.failure_category,
        "safe_failure_message": run.safe_failure_message,
        "resumable_from": run.resumable_from,
    }
    if metrics is not None:
        body["metrics"] = metrics
    return body


def model_view(m: ModelVersion) -> dict[str, Any]:
    return {
        "model_version": m.model_version,
        "model_type": m.model_type,
        "target_definition": m.target_definition,
        "feature_version": m.feature_version,
        "feature_regime": m.feature_regime,
        "training_dataset_id": str(m.training_dataset_id),
        "training_snapshot_ids": m.training_snapshot_ids,
        "split_boundaries": m.split_boundaries,
        "training_config": m.training_config,
        "class_distribution": m.class_distribution,
        "evaluation_metrics": m.evaluation_metrics,
        "operating_threshold": str(m.operating_threshold),
        "artifact_reference": m.artifact_reference,
        "artifact_sha256": m.artifact_sha256,
        "implementation_version": m.implementation_version,
        "random_seed": m.random_seed,
        "created_at": _iso(m.created_at),
    }


class JobService:
    def __init__(self, settings: Settings, audit: AuditService) -> None:
        self.settings = settings
        self.audit = audit

    # ── pipeline runs ──────────────────────────────────────────────────────

    def start_pipeline(
        self, db: Session, actor: Principal, dataset_id: uuid.UUID, request_id: str | None
    ) -> PipelineRun:
        dataset = db.get(Dataset, dataset_id, with_for_update=True)
        if dataset is None:
            raise AppError(ec.NOT_FOUND, details={"resource": "dataset"})
        self.ensure_no_active_run(db, dataset_id)
        if latest_succeeded_ingestion(db, dataset_id) is None:
            raise AppError(ec.PIPELINE_PREREQUISITE_MISSING, details={"prerequisite": "ingestion"})
        run = self.create_run(db, dataset_id, None)
        enqueue_stage(
            db, run, "INGESTING", self.settings.job_max_attempts, requested_by=actor.user_id, request_id=request_id
        )
        self.audit.record_in(
            db,
            "pipeline.start",
            "pipeline_run",
            "SUCCESS",
            user_id=actor.user_id,
            resource_id=str(run.pipeline_run_id),
            metadata={"dataset_id": str(dataset_id)},
        )
        db.commit()
        return run

    @staticmethod
    def ensure_no_active_run(db: Session, dataset_id: uuid.UUID) -> None:
        active = db.execute(
            select(func.count())
            .select_from(PipelineRun)
            .where(PipelineRun.dataset_id == dataset_id, PipelineRun.current_state.not_in(TERMINAL))
        ).scalar_one()
        if active:
            raise AppError(ec.PIPELINE_ALREADY_RUNNING)

    @staticmethod
    def create_run(db: Session, dataset_id: uuid.UUID, ingestion_run_id: uuid.UUID | None) -> PipelineRun:
        now = utcnow()
        run = PipelineRun(
            pipeline_run_id=uuid.uuid4(),
            dataset_id=dataset_id,
            ingestion_run_id=ingestion_run_id,
            current_state="CREATED",
            started_at=now,
            updated_at=now,
        )
        db.add(run)
        db.flush()
        return run

    def retry(self, db: Session, actor: Principal, run_id: uuid.UUID, request_id: str | None) -> PipelineRun:
        run = db.get(PipelineRun, run_id, with_for_update=True)
        if run is None:
            raise AppError(ec.NOT_FOUND, details={"resource": "pipeline_run"})
        if run.current_state != "FAILED" or run.resumable_from not in RUNNING_STATES:
            raise AppError(
                ec.CONFLICT,
                "Only a failed pipeline run with a resume point can be retried.",
                {"current_state": run.current_state},
            )
        stage = REGISTRY[str(run.resumable_from)]
        if not stage.prerequisites_ok(db, run):
            raise AppError(ec.PIPELINE_PREREQUISITE_MISSING, details={"stage": stage.name})
        others = db.execute(
            select(func.count())
            .select_from(PipelineRun)
            .where(
                PipelineRun.dataset_id == run.dataset_id,
                PipelineRun.pipeline_run_id != run.pipeline_run_id,
                PipelineRun.current_state.not_in(TERMINAL),
            )
        ).scalar_one()
        if others:
            raise AppError(ec.PIPELINE_ALREADY_RUNNING)
        run.current_state = advance("FAILED", stage.name)
        run.updated_at = utcnow()
        enqueue_stage(
            db, run, stage.name, self.settings.job_max_attempts, requested_by=actor.user_id, request_id=request_id
        )
        self.audit.record_in(
            db,
            "pipeline.retry",
            "pipeline_run",
            "SUCCESS",
            user_id=actor.user_id,
            resource_id=str(run.pipeline_run_id),
            metadata={"stage": stage.name},
        )
        db.commit()
        return run

    def get_run(self, db: Session, run_id: uuid.UUID) -> PipelineRun:
        run = db.get(PipelineRun, run_id)
        if run is None:
            raise AppError(ec.NOT_FOUND, details={"resource": "pipeline_run"})
        return run

    def list_runs(
        self, db: Session, page: PageRequest, dataset_id: uuid.UUID | None, state: str | None
    ) -> tuple[list[PipelineRun], int]:
        q = select(PipelineRun)
        if dataset_id is not None:
            q = q.where(PipelineRun.dataset_id == dataset_id)
        if state is not None:
            q = q.where(PipelineRun.current_state == state)
        total = int(db.execute(select(func.count()).select_from(q.subquery())).scalar_one())
        rows = db.execute(
            q.order_by(PipelineRun.started_at.desc(), PipelineRun.pipeline_run_id)
            .offset(page.offset)
            .limit(page.page_size)
        ).scalars()
        return list(rows), total

    def metrics(self, db: Session, run: PipelineRun) -> dict[str, Any]:
        """§24.2 metrics collected so far."""
        out: dict[str, Any] = {}
        if run.ingestion_run_id is not None:
            ing = db.get(IngestionRun, run.ingestion_run_id)
            if ing is not None:
                out.update(
                    records_seen=ing.records_seen,
                    records_accepted=ing.records_accepted,
                    records_rejected=ing.records_rejected,
                    records_rejected_by_reason=ing.rejection_summary.get("counts", {}),
                    records_duplicate=ing.records_duplicate,
                )
        if run.graph_snapshot_id is not None:
            snap = db.get(GraphSnapshot, run.graph_snapshot_id)
            if snap is not None:
                out.update(
                    graph_nodes=snap.node_count, graph_edges=snap.edge_count, validation_digest=snap.validation_digest
                )
        rows = db.execute(
            text(
                "SELECT payload->>'stage' AS stage, attempts, failure_category, "
                "EXTRACT(EPOCH FROM (completed_at - started_at)) AS seconds, status "
                "FROM jobs WHERE payload->>'pipeline_run_id' = :rid ORDER BY created_at"
            ),
            {"rid": str(run.pipeline_run_id)},
        ).all()
        durations: dict[str, float | None] = {}
        for r in rows:
            name = STAGE_METRIC.get(r.stage)
            if name is not None and r.status == "SUCCEEDED" and r.seconds is not None:
                durations[name] = round(float(r.seconds), 3)
        out.update(durations)
        out["job_attempts"] = int(sum(r.attempts for r in rows))
        out["lease_expirations"] = sum(1 for r in rows if r.failure_category == "LEASE_EXPIRED")
        out["failure_stage"] = run.failure_stage
        out["failure_category"] = run.failure_category
        return out

    # ── models and context ─────────────────────────────────────────────────

    @staticmethod
    def list_models(db: Session, page: PageRequest) -> tuple[list[ModelVersion], int]:
        total = int(db.execute(select(func.count()).select_from(ModelVersion)).scalar_one())
        rows = db.execute(
            select(ModelVersion)
            .order_by(ModelVersion.created_at.desc(), ModelVersion.model_version)
            .offset(page.offset)
            .limit(page.page_size)
        ).scalars()
        return list(rows), total

    @staticmethod
    def get_model(db: Session, version: str) -> ModelVersion:
        m = db.get(ModelVersion, version)
        if m is None:
            raise AppError(ec.NOT_FOUND, details={"resource": "model"})
        return m

    @staticmethod
    def active_context(db: Session) -> dict[str, Any]:
        ctx = db.execute(select(ActiveContext)).scalar_one()
        dataset = None if ctx.dataset_id is None else db.get(Dataset, ctx.dataset_id)
        return {
            "dataset_id": _str(ctx.dataset_id),
            "graph_snapshot_id": _str(ctx.graph_snapshot_id),
            "analytics_run_id": _str(ctx.analytics_run_id),
            "scoring_run_id": _str(ctx.scoring_run_id),
            "model_version": ctx.model_version,
            "risk_logic_version": ctx.risk_logic_version,
            "updated_at": _iso(ctx.updated_at),
            "updated_by_pipeline_run_id": _str(ctx.updated_by_pipeline_run_id),
            "is_active": ctx.dataset_id is not None,
            # §7.10 rule 3: the UI labels a synthetic-injection context SYNTHETIC DATA
            "is_synthetic_injection": bool(dataset is not None and dataset.is_synthetic_injection),
        }
