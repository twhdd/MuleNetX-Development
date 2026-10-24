"""Router registration. Each task adds its routers here."""

from __future__ import annotations

from fastapi import FastAPI

from mulenetx.api.routes import (
    accounts,
    aliases,
    audit,
    auth,
    cases,
    communities,
    context,
    copilot,
    evaluation,
    graph,
    health,
    ingestion,
    interventions,
    models,
    motifs,
    pipelines,
    rings,
    users,
)


def register_routes(app: FastAPI) -> None:
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(ingestion.router)
    app.include_router(pipelines.router)
    app.include_router(models.router)
    app.include_router(context.router)
    app.include_router(accounts.router)
    app.include_router(graph.router)
    app.include_router(communities.router)
    app.include_router(cases.router)
    app.include_router(motifs.router)
    app.include_router(rings.router)
    app.include_router(interventions.router)
    app.include_router(evaluation.router)
    app.include_router(copilot.router)
    app.include_router(audit.router)
    app.include_router(aliases.router)
