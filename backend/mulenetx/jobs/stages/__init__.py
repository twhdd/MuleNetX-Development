"""Stage registry: running state -> stage (SRS §7.6)."""

from __future__ import annotations

from mulenetx.jobs.stages.analytics import AnalyticsStage
from mulenetx.jobs.stages.base import Stage
from mulenetx.jobs.stages.features import FeaturesStage
from mulenetx.jobs.stages.graph_build import GraphBuildStage
from mulenetx.jobs.stages.ingest import IngestStage
from mulenetx.jobs.stages.profile import ProfileStage
from mulenetx.jobs.stages.ring_analysis import RingAnalysisStage
from mulenetx.jobs.stages.scoring import ScoringStage
from mulenetx.jobs.stages.training import TrainingStage

REGISTRY: dict[str, Stage] = {
    stage.name: stage
    for stage in (
        IngestStage(),
        ProfileStage(),
        GraphBuildStage(),
        AnalyticsStage(),
        FeaturesStage(),
        TrainingStage(),
        ScoringStage(),
        RingAnalysisStage(),
    )
}
