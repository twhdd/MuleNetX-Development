"""Stage contract (PLAN §7.4) and the context handed to a stage."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.pipeline import PipelineRun
from mulenetx.jobs.runner import JobContext

Finalizer = Callable[[Session], None]


@dataclass
class StageContext:
    runtime: Runtime
    job: JobContext
    pipeline_run_id: uuid.UUID
    dataset_id: uuid.UUID
    payload: dict[str, Any]

    def run(self, session: Session) -> PipelineRun:
        run = session.get(PipelineRun, self.pipeline_run_id)
        if run is None:
            raise LookupError(f"pipeline run {self.pipeline_run_id} not found")
        return run

    def load_run(self) -> PipelineRun:
        with self.runtime.session_factory() as session:
            return self.run(session)

    def set_once(self, column: str, value: Any) -> Any:
        """Set a 'Set once' pipeline-run column if it is NULL; return the stored value."""
        with self.runtime.session_factory() as session:
            run = self.run(session)
            current = getattr(run, column)
            if current is not None:
                return current
            session.execute(
                update(PipelineRun)
                .where(PipelineRun.pipeline_run_id == self.pipeline_run_id)
                .values({column: value, "updated_at": utcnow()})
            )
            session.commit()
            return value

    def check(self) -> None:
        self.job.check()


@dataclass
class StageOutcome:
    """What the stage hands to the final transaction: run columns to set and extra final writes."""

    run_updates: dict[str, Any] = field(default_factory=dict)
    finalize: Finalizer | None = None
    next_payload: dict[str, Any] = field(default_factory=dict)


class Stage(ABC):
    name: str  # running state, e.g. "ANALYTICS_RUNNING"
    kind: str = "PIPELINE_STAGE"

    def prerequisites_ok(self, session: Session, run: PipelineRun) -> bool:
        return True

    def delete_partial_outputs(self, ctx: StageContext) -> None:  # noqa: B027 - optional hook
        """Delete outputs of a previous failed attempt keyed by this stage's run identifier (§7.7)."""

    @abstractmethod
    def execute(self, ctx: StageContext) -> StageOutcome:
        """Idempotent work; writes keyed by run ids; returns the final-transaction outcome."""

    def on_failure(self, runtime: Runtime, run: PipelineRun, category: str, message: str) -> None:  # noqa: B027
        """Mark stage-owned resources failed (for example the ingestion run)."""
