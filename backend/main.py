from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.environment_validator import (
    validate_environment
)

from backend.middleware.metrics import (
    metrics_middleware
)

from backend.middleware.rate_limit import (
    rate_limit_middleware
)

from backend.routes.admin import (
    router as admin_router
)

from backend.routes.auth import (
    router as auth_router
)

from backend.routes.cases import (
    router as case_router
)

from backend.routes.community import (
    router as community_router
)

from backend.routes.copilot import (
    router as copilot_router
)

from backend.routes.dashboard import (
    router as dashboard_router
)

from backend.routes.graph import (
    router as graph_router
)

from backend.routes.internal import (
    router as internal_router
)

from backend.routes.investigation import (
    router as investigation_router
)

from backend.routes.live_alerts import (
    router as alert_router
)

from backend.routes.live_transactions import (
    router as live_tx_router
)

from backend.routes.metrics import (
    router as metrics_router
)

from backend.routes.network import (
    router as network_router
)

from backend.routes.patterns import (
    router as pattern_router
)

from backend.routes.report import (
    router as report_router
)

from backend.routes.risk import (
    router as risk_router
)

from backend.routes.search import (
    router as search_router
)

from backend.routes.simulation import (
    router as simulation_router
)

from backend.routes.snapshot import (
    router as snapshot_router
)

from backend.routes.stream import (
    router as stream_router
)

from backend.routes.token import (
    router as token_router
)

from backend.routes.websocket import (
    router as websocket_router
)

validate_environment()

app = FastAPI(
    title="MuleNetX",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.middleware("http")(
    rate_limit_middleware
)

app.middleware("http")(
    metrics_middleware
)

app.include_router(auth_router, prefix="/api")
app.include_router(token_router, prefix="/api")

app.include_router(investigation_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(copilot_router, prefix="/api")
app.include_router(report_router, prefix="/api")

app.include_router(graph_router, prefix="/api")
app.include_router(network_router, prefix="/api")
app.include_router(community_router, prefix="/api")

app.include_router(pattern_router, prefix="/api")
app.include_router(simulation_router, prefix="/api")

app.include_router(case_router, prefix="/api")

app.include_router(alert_router, prefix="/api")
app.include_router(stream_router, prefix="/api")
app.include_router(live_tx_router, prefix="/api")
app.include_router(internal_router, prefix="/api")

app.include_router(search_router, prefix="/api")

app.include_router(snapshot_router, prefix="/api")
app.include_router(metrics_router)
app.include_router(admin_router, prefix="/api")

app.include_router(websocket_router)


@app.get("/")
def health():

    return {
        "name": "MuleNetX",
        "status": "running",
        "version": "1.0.0"
    }
