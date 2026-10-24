"""Pagination contract (SRS §19.11)."""

from datetime import UTC, datetime

import pytest

from mulenetx.core.errors import AppError
from mulenetx.core.pagination import cap_total, decode_cursor, encode_cursor, offset_page, page_request


def test_total_capped_at_cap() -> None:
    assert cap_total(10_001, 10_000) == (10_000, True)
    assert cap_total(10_000, 10_000) == (10_000, False)
    assert cap_total(3, 10_000) == (3, False)


def test_offset_page_shape() -> None:
    req = page_request(2, 25, 25, 100)
    body = offset_page([1, 2], req, 20_000, 10_000)
    assert body == {"items": [1, 2], "page": 2, "page_size": 25, "total": 10_000, "total_is_capped": True}
    assert req.offset == 25


def test_page_size_above_max_rejected_not_clamped() -> None:
    with pytest.raises(AppError) as err:
        page_request(1, 101, 25, 100)
    assert err.value.code == "LIMIT_EXCEEDED"
    assert err.value.http_status == 400


def test_defaults() -> None:
    req = page_request(None, None, 25, 100)
    assert (req.page, req.page_size) == (1, 25)


def test_cursor_roundtrip() -> None:
    ts = datetime(2020, 1, 1, 5, tzinfo=UTC)
    cursor = encode_cursor(ts, "d:0000000007")
    assert decode_cursor(cursor) == (ts, "d:0000000007")


def test_bad_cursor() -> None:
    with pytest.raises(AppError) as err:
        decode_cursor("not-a-cursor!!")
    assert err.value.code == "VALIDATION_ERROR"
