"""Application error and the standard error envelope (SRS §19.3)."""

from __future__ import annotations

from typing import Any

from mulenetx.core import error_codes as ec


class AppError(Exception):
    """An error with a stable code that maps to an HTTP status and the §19.3 envelope.

    `details` may contain only field names and limit values (SRS §19.3).
    """

    def __init__(
        self,
        code: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        http_status: int | None = None,
    ) -> None:
        spec = ec.ERRORS[code]
        self.code = code
        self.http_status = http_status if http_status is not None else spec.http_status
        self.message = message if message is not None else spec.message
        self.details: dict[str, Any] = dict(details or {})
        super().__init__(f"{code}: {self.message}")


def limit_exceeded(field: str, limit: int | float | str) -> AppError:
    return AppError(ec.LIMIT_EXCEEDED, details={"field": field, "limit": limit})


def not_found(resource: str) -> AppError:
    return AppError(ec.NOT_FOUND, details={"resource": resource})


def error_body(code: str, message: str, request_id: str | None, details: dict[str, Any]) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "request_id": request_id, "details": details}}
