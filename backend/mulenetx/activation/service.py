"""Activation of a READY pipeline run (SRS §6.9) — one PostgreSQL transaction:

1. update `active_context` to the run's dataset, snapshot, analytics run, scoring run, model, risk logic;
2. update the `accounts` projection columns of the dataset from the run's assessments and community
   memberships;
3. write the `pipeline.activate` audit event.

Then the previous OPERATIONAL snapshot is queued for retirement (SNAPSHOT_RETIRE), in the same transaction.
Any failure rolls everything back and the previous context stays active.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from mulenetx.audit.service import AuditService
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.lineage import ActiveContext, GraphSnapshot, ScoringRun
from mulenetx.db.models.pipeline import PipelineRun
from mulenetx.jobs import queue


def update_projections(session: Session, run: PipelineRun) -> None:
    """Step 2: one pass over the dataset's accounts (accounts without an assessment or a community get NULL)."""
    session.execute(
        text(
            """
            UPDATE accounts a
            SET risk_score = x.final_score, risk_tier = x.risk_tier,
                latest_risk_assessment_id = x.assessment_id, community_id = x.community_id
            FROM (
                SELECT acc.account_id, ra.final_score, ra.risk_tier, ra.assessment_id, cm.community_id
                FROM accounts acc
                LEFT JOIN risk_assessments ra ON ra.account_id = acc.account_id AND ra.scoring_run_id = :scoring
                LEFT JOIN community_memberships cm
                       ON cm.account_id = acc.account_id AND cm.analytics_run_id = :analytics
                WHERE acc.dataset_id = :dataset
            ) x
            WHERE a.account_id = x.account_id
              AND (a.risk_score IS DISTINCT FROM x.final_score OR a.risk_tier IS DISTINCT FROM x.risk_tier
                   OR a.latest_risk_assessment_id IS DISTINCT FROM x.assessment_id
                   OR a.community_id IS DISTINCT FROM x.community_id)
            """
        ),
        {"scoring": run.scoring_run_id, "analytics": run.analytics_run_id, "dataset": run.dataset_id},
    )


def activate(session: Session, run: PipelineRun, max_attempts: int) -> None:
    ctx = session.execute(select(ActiveContext).with_for_update()).scalar_one()
    previous_snapshot = ctx.graph_snapshot_id
    risk_logic_version = None
    model_version = run.model_version
    if run.scoring_run_id is not None:
        scoring = session.get(ScoringRun, run.scoring_run_id)
        if scoring is not None:
            risk_logic_version = scoring.risk_logic_version
            model_version = scoring.model_version  # NULL when the ML component was unavailable
    session.execute(
        update(ActiveContext)
        .where(ActiveContext.singleton.is_(True))
        .values(
            dataset_id=run.dataset_id,
            graph_snapshot_id=run.graph_snapshot_id,
            analytics_run_id=run.analytics_run_id,
            scoring_run_id=run.scoring_run_id,
            model_version=model_version,
            risk_logic_version=risk_logic_version,
            updated_at=utcnow(),
            updated_by_pipeline_run_id=run.pipeline_run_id,
        )
    )
    update_projections(session, run)
    session.add(
        AuditService.build(
            "pipeline.activate",
            "pipeline_run",
            "SUCCESS",
            resource_id=str(run.pipeline_run_id),
            metadata={
                "dataset_id": str(run.dataset_id),
                "graph_snapshot_id": str(run.graph_snapshot_id),
                "scoring_run_id": None if run.scoring_run_id is None else str(run.scoring_run_id),
                "previous_graph_snapshot_id": None if previous_snapshot is None else str(previous_snapshot),
            },
        )
    )
    if previous_snapshot is not None and previous_snapshot != run.graph_snapshot_id:
        previous = session.get(GraphSnapshot, previous_snapshot)
        if previous is not None and previous.purpose == "OPERATIONAL" and previous.status == "READY":
            enqueue_retirement(session, previous_snapshot, max_attempts)


def enqueue_retirement(session: Session, snapshot_id: uuid.UUID, max_attempts: int) -> None:
    queue.enqueue(session, "SNAPSHOT_RETIRE", {"graph_snapshot_id": str(snapshot_id)}, max_attempts=max_attempts)
