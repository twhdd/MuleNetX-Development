"""SNAPSHOT_RETIRE job (SRS §6.8.6)."""

from __future__ import annotations

import uuid

from mulenetx.audit.service import AuditService
from mulenetx.core.runtime import Runtime
from mulenetx.graph.service import GraphService
from mulenetx.jobs.runner import JobContext


class SnapshotRetireHandler:
    def run(self, ctx: JobContext) -> None:
        snapshot_id = uuid.UUID(str(ctx.job.payload["graph_snapshot_id"]))
        GraphService(ctx.runtime).retire(snapshot_id, ctx.check)
        with ctx.runtime.session_factory() as session:
            session.add(
                AuditService.build(
                    "snapshot.retire",
                    "graph_snapshot",
                    "SUCCESS",
                    resource_id=str(snapshot_id),
                    request_id=ctx.job.request_id,
                )
            )
            ctx.complete(session)
            session.commit()

    def on_failure(
        self, runtime: Runtime, job_id: uuid.UUID, payload: dict[str, object], category: str, message: str
    ) -> None:
        return None
