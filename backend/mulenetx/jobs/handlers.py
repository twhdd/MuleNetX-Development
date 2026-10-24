"""Job-kind → handler registry. Each task registers its handlers here."""

from __future__ import annotations

from mulenetx.jobs.evaluation_handler import EvaluationHandler
from mulenetx.jobs.intervention_handler import InterventionHandler
from mulenetx.jobs.pipeline_handler import PipelineStageHandler
from mulenetx.jobs.retire_handler import SnapshotRetireHandler
from mulenetx.jobs.runner import Handler


def build_handlers() -> dict[str, Handler]:
    pipeline = PipelineStageHandler()
    return {
        "INGEST": pipeline,
        "PIPELINE_STAGE": pipeline,
        "TRAIN": pipeline,
        "SNAPSHOT_RETIRE": SnapshotRetireHandler(),
        "INTERVENTION": InterventionHandler(),
        "EVALUATION": EvaluationHandler(),
    }
