"""Pagination contract (SRS §19.11).

Offset pages: `{items, page, page_size, total, total_is_capped}` with `total` capped at
`pagination_count_cap`. Cursor pages: `{items, next_cursor}` where the cursor is base64url JSON of
the last `(timestamp, transaction_id)`. Above-limit parameters are rejected, never clamped (§19.1).
"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError, limit_exceeded
from mulenetx.core.timeutil import isoformat_utc, parse_utc


@dataclass(frozen=True)
class PageRequest:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_request(page: int | None, page_size: int | None, default_size: int, max_size: int) -> PageRequest:
    p = 1 if page is None else page
    size = default_size if page_size is None else page_size
    if p < 1:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "page"})
    if size < 1:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "page_size"})
    if size > max_size:
        raise limit_exceeded("page_size", max_size)
    return PageRequest(page=p, page_size=size)


def cap_total(total: int, cap: int) -> tuple[int, bool]:
    """Return (total, total_is_capped) per §19.11."""
    if total > cap:
        return cap, True
    return total, False


def offset_page(items: list[Any], req: PageRequest, total: int, cap: int) -> dict[str, Any]:
    capped_total, is_capped = cap_total(total, cap)
    return {
        "items": items,
        "page": req.page,
        "page_size": req.page_size,
        "total": capped_total,
        "total_is_capped": is_capped,
    }


def encode_cursor(timestamp: datetime, transaction_id: str) -> str:
    raw = json.dumps({"t": isoformat_utc(timestamp), "id": transaction_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        return parse_utc(str(data["t"])), str(data["id"])
    except (ValueError, KeyError, TypeError, binascii.Error, json.JSONDecodeError) as exc:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "cursor"}) from exc
