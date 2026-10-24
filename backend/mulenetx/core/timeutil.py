"""Time helpers (SRS §3.4, §15.1).

Event time and processing time are never compared. Every timestamp is timezone-aware UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

HOUR = timedelta(hours=1)


def utcnow() -> datetime:
    """Processing time. Use only for created_at/computed_at/... fields (§3.4)."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("naive datetime; every timestamp must be timezone-aware UTC")
    return value.astimezone(UTC)


def parse_utc(text: str) -> datetime:
    return ensure_utc(datetime.fromisoformat(text.replace("Z", "+00:00")))


def isoformat_utc(value: datetime) -> str:
    return ensure_utc(value).isoformat().replace("+00:00", "Z")


def hour_bucket(value: datetime) -> datetime:
    """Start of the UTC-aligned hour containing `value`."""
    v = ensure_utc(value)
    return v.replace(minute=0, second=0, microsecond=0)


def floor_to_resolution(value: datetime, resolution_seconds: int) -> datetime:
    """Round an event time down to the dataset timestamp resolution (SRS §11.4)."""
    v = ensure_utc(value)
    epoch = int(v.timestamp())
    floored = epoch - (epoch % resolution_seconds)
    return datetime.fromtimestamp(floored, UTC)
