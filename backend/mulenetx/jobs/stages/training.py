"""TRAINING stage (SRS §11; §7.6 rules 3–4). Runs only when no compatible model is registered; a training
failure still creates the risk logic version, and SCORING then runs with the ML component unavailable."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from mulenetx.activation.service import enqueue_retirement
from mulenetx.audit.service import AuditService
from mulenetx.db.models.datasets import Dataset
from mulenetx.db.models.pipeline import PipelineRun
from mulenetx.jobs.stages.base import Stage, StageContext, StageOutcome
from mulenetx.ml.registry import compatible_model as registry_compatible_model
from mulenetx.ml.train import TrainingService

logger = logging.getLogger("mulenetx.ml")


def compatible_model(session: Session, run: PipelineRun) -> str | None:
    """§7.6 rule 3: a registered model with the current feature version, regime and target definition."""
    model = registry_compatible_model(session)
    return None if model is None else model.model_version


class TrainingStage(Stage):
    name = "TRAINING"
    kind = "TRAIN"

    def execute(self, ctx: StageContext) -> StageOutcome:
        run = ctx.load_run()
        assert run.ingestion_run_id is not None
        with ctx.runtime.session_factory() as session:
            dataset = session.get(Dataset, ctx.dataset_id)
            assert dataset is not None
            resolution = dataset.timestamp_resolution_seconds
            session.add(
                AuditService.build(
                    "model.training_start", "pipeline_run", "SUCCESS", resource_id=str(run.pipeline_run_id)
                )
            )
            session.commit()
        try:
            outcome = TrainingService(ctx.runtime).train(ctx.dataset_id, run.ingestion_run_id, resolution, ctx.check)
        except Exception as exc:  # noqa: BLE001 - rule 4: scoring still runs with the ML component unavailable
            logger.exception("training failed")
            from mulenetx.ml.train import create_risk_logic_version

            rl = create_risk_logic_version(
                ctx.runtime, {"model_version": None, "training_failure": f"training error: {type(exc).__name__}"}
            )
            return StageOutcome(next_payload={"risk_logic_version": rl})
        max_attempts = ctx.runtime.settings.job_max_attempts

        def finalize(session: Session) -> None:
            if outcome.model_version is not None:
                session.add(
                    AuditService.build(
                        "model.register",
                        "model_version",
                        "SUCCESS",
                        resource_id=outcome.model_version,
                        metadata={"risk_logic_version": outcome.risk_logic_version},
                    )
                )
            else:
                session.add(
                    AuditService.build(
                        "model.register",
                        "model_version",
                        "FAILED",
                        resource_id=None,
                        metadata={"reason": outcome.failure_reason},
                    )
                )
            for snapshot_id in outcome.training_snapshot_ids:
                enqueue_retirement(session, snapshot_id, max_attempts)

        updates = {"model_version": outcome.model_version} if outcome.model_version else {}
        return StageOutcome(
            run_updates=updates, finalize=finalize, next_payload={"risk_logic_version": outcome.risk_logic_version}
        )
