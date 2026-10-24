"""INTERVENTION job (SRS §16A.2, §7.8): computes one scenario and writes its results in one transaction."""

from __future__ import annotations

import uuid

from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.interventions import InterventionScenario
from mulenetx.interventions.metrics import money4
from mulenetx.interventions.pool import PoolTooLargeError
from mulenetx.interventions.service import candidate_row, run_scenario
from mulenetx.jobs.runner import JobContext, JobFailedError


class InterventionHandler:
    def run(self, ctx: JobContext) -> None:
        scenario_id = uuid.UUID(str(ctx.job.payload["scenario_id"]))
        rt = ctx.runtime
        with rt.session_factory() as db:
            scenario = db.get(InterventionScenario, scenario_id, with_for_update=True)
            if scenario is None:
                raise JobFailedError("INTERNAL", "scenario not found")
            if scenario.status == "QUEUED":
                scenario.status = "RUNNING"
                db.commit()
        with rt.session_factory() as db:
            scenario = db.get(InterventionScenario, scenario_id)
            assert scenario is not None
            try:
                base, results, eligible = run_scenario(rt.engine, rt.settings, db, scenario)
            except PoolTooLargeError as exc:
                raise JobFailedError("LIMIT_EXCEEDED", str(exc)) from exc
            db.rollback()
        ctx.check()
        now = utcnow()
        with rt.session_factory() as db:
            scenario = db.get(InterventionScenario, scenario_id, with_for_update=True)
            assert scenario is not None
            scenario.baseline_suspicious_flow = money4(base.suspicious_flow)
            scenario.baseline_suspicious_paths = len(base.paths)
            scenario.baseline_reachable_suspicious_pairs = len(base.pairs)
            scenario.baseline_risk_mass = base.risk_mass
            scenario.baseline_paths_truncated = base.truncated
            scenario.eligible_candidate_ids = eligible
            scenario.status = "COMPLETED"
            scenario.completed_at = now
            db.add_all(candidate_row(scenario_id, r, now) for r in results)
            ctx.complete(db)
            db.commit()

    def on_failure(
        self, runtime: Runtime, job_id: uuid.UUID, payload: dict[str, object], category: str, message: str
    ) -> None:
        scenario_id = uuid.UUID(str(payload["scenario_id"]))
        with runtime.session_factory() as db:
            scenario = db.get(InterventionScenario, scenario_id, with_for_update=True)
            if scenario is not None and scenario.status in ("QUEUED", "RUNNING"):
                scenario.status = "FAILED"
                scenario.error_summary = f"{category}: {message}"[:500]
                scenario.completed_at = utcnow()
                db.commit()
