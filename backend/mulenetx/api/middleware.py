"""Request middleware: request ID, structured request log, per-route body-size limit (SRS §19.1, §24.1)."""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from collections.abc import Callable
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import error_body
from mulenetx.core.logging import log_fields, request_id_var, user_id_var

logger = logging.getLogger("mulenetx.request")

KIB = 1024
DEFAULT_BODY_LIMIT = 64 * KIB  # agent default for routes without an SRS limit (OQ-05)
MULTIPART_OVERHEAD = 64 * KIB


def route_body_limits(max_upload_bytes: int) -> list[tuple[str, re.Pattern[str], int]]:
    """Body limits from SRS §19.2 (method, path pattern, bytes)."""
    return [
        ("POST", re.compile(r"^/api/v1/auth/login$"), 4 * KIB),
        ("POST", re.compile(r"^/api/v1/users$"), 4 * KIB),
        ("PATCH", re.compile(r"^/api/v1/users/[^/]+$"), 4 * KIB),
        ("POST", re.compile(r"^/api/v1/cases$"), 16 * KIB),
        ("PATCH", re.compile(r"^/api/v1/cases/[^/]+$"), 16 * KIB),
        ("POST", re.compile(r"^/api/v1/cases/[^/]+/findings$"), 64 * KIB),
        ("POST", re.compile(r"^/api/v1/ingestion$"), max_upload_bytes + MULTIPART_OVERHEAD),
    ]


class BodyTooLargeError(Exception):
    pass


def is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, max_upload_bytes: int) -> None:
        self.app = app
        self.limits = route_body_limits(max_upload_bytes)

    def _limit_for(self, method: str, path: str) -> int:
        for m, pattern, limit in self.limits:
            if m == method and pattern.match(path):
                return limit
        return DEFAULT_BODY_LIMIT

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        supplied = headers.get("x-request-id", "")
        request_id = supplied if is_valid_uuid(supplied) else str(uuid.uuid4())
        rid_token = request_id_var.set(request_id)
        uid_token = user_id_var.set(None)
        state: dict[str, Any] = scope.setdefault("state", {})
        state["request_id"] = request_id

        method: str = scope["method"]
        path: str = scope["path"]
        limit = self._limit_for(method, path)
        started = time.perf_counter()
        status_holder: dict[str, Any] = {"status": 500, "started": False}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                status_holder["started"] = True
                raw_headers = list(message.get("headers", []))
                raw_headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = raw_headers
            await send(message)

        try:
            declared = headers.get("content-length")
            if declared is not None and declared.isdigit() and int(declared) > limit:
                await self._reject_too_large(send_wrapper, request_id, limit)
                return
            received = 0

            async def receive_wrapper() -> Message:
                nonlocal received
                message = await receive()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > limit:
                        raise BodyTooLargeError()
                return message

            try:
                await self.app(scope, receive_wrapper, send_wrapper)
            except BodyTooLargeError:
                if not status_holder["started"]:
                    await self._reject_too_large(send_wrapper, request_id, limit)
                    state["error_category"] = ec.PAYLOAD_TOO_LARGE
        finally:
            route = scope.get("route")
            endpoint = getattr(route, "path", path)
            log_fields(
                logger,
                logging.INFO,
                "request",
                endpoint=endpoint,
                operation=method,
                status=status_holder["status"],
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                error_category=state.get("error_category"),
                user_id=state.get("user_id") or user_id_var.get(),
            )
            request_id_var.reset(rid_token)
            user_id_var.reset(uid_token)

    @staticmethod
    async def _reject_too_large(send: Callable[[Message], Any], request_id: str, limit: int) -> None:
        spec = ec.ERRORS[ec.PAYLOAD_TOO_LARGE]
        body = json.dumps(error_body(spec.code, spec.message, request_id, {"limit": limit})).encode()
        await send(
            {
                "type": "http.response.start",
                "status": spec.http_status,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
            }
        )
        await send({"type": "http.response.body", "body": body})
