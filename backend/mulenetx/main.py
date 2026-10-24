"""FastAPI application factory: middleware, error handlers and routers (SRS §18.3, §19)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from mulenetx.api.middleware import RequestContextMiddleware
from mulenetx.core import error_codes as ec
from mulenetx.core.config import Settings, get_settings
from mulenetx.core.errors import AppError, error_body
from mulenetx.core.logging import configure_logging, request_id_var
from mulenetx.core.runtime import Runtime

logger = logging.getLogger("mulenetx.api")


def _request_id(request: Request) -> str | None:
    rid = request.scope.get("state", {}).get("request_id")
    return rid if isinstance(rid, str) else request_id_var.get()


def _mark_error(request: Request, code: str) -> None:
    request.scope.setdefault("state", {})["error_category"] = code


def _envelope(request: Request, code: str, message: str, status: int, details: dict[str, Any]) -> JSONResponse:
    _mark_error(request, code)
    return JSONResponse(status_code=status, content=error_body(code, message, _request_id(request), details))


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return _envelope(request, exc.code, exc.message, exc.http_status, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = sorted({".".join(str(p) for p in err.get("loc", ()) if p != "body") for err in exc.errors()})
        spec = ec.ERRORS[ec.VALIDATION_ERROR]
        return _envelope(request, spec.code, spec.message, spec.http_status, {"fields": fields})

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = ec.GENERIC_BY_STATUS.get(exc.status_code, ec.VALIDATION_ERROR if exc.status_code < 500 else ec.INTERNAL)
        spec = ec.ERRORS[code]
        return _envelope(request, code, spec.message, exc.status_code, {})

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error")
        spec = ec.ERRORS[ec.INTERNAL]
        return _envelope(request, spec.code, spec.message, spec.http_status, {})


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings if settings is not None else get_settings()
    configure_logging(cfg.log_level)
    runtime = Runtime(cfg)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        runtime.close()

    app = FastAPI(title="MuleNetX", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = cfg
    app.state.runtime = runtime
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Deprecation", "Link"],
    )
    app.add_middleware(RequestContextMiddleware, max_upload_bytes=cfg.max_upload_bytes)
    from mulenetx.api.routes import register_routes

    register_routes(app)
    from mulenetx.openapi import install as install_openapi

    install_openapi(app)
    return app


_app: FastAPI | None = None


def __getattr__(name: str) -> Any:
    # `uvicorn mulenetx.main:app` builds the app lazily so that importing this module never reads
    # the environment (tests construct apps with explicit settings).
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(name)
