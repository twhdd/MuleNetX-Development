"""Copilot capacity (SRS §21.7): a global semaphore with a 2 s wait (429 COPILOT_BUSY) and a per-user rate."""

from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError


class Limiter:
    def __init__(self, concurrency: int, wait_seconds: float, per_minute: int) -> None:
        self.semaphore = threading.BoundedSemaphore(concurrency)
        self.wait_seconds = wait_seconds
        self.per_minute = per_minute
        self._lock = threading.Lock()
        self._recent: dict[uuid.UUID, deque[float]] = {}

    def check_rate(self, user_id: uuid.UUID, now: float | None = None) -> None:
        t = time.monotonic() if now is None else now
        with self._lock:
            q = self._recent.setdefault(user_id, deque())
            while q and t - q[0] >= 60:
                q.popleft()
            if len(q) >= self.per_minute:
                raise AppError(
                    ec.RATE_LIMITED,
                    "Copilot rate limit reached; retry in a minute.",
                    {"limit_per_minute": self.per_minute},
                )
            q.append(t)

    @contextmanager
    def slot(self) -> Iterator[None]:
        if not self.semaphore.acquire(timeout=self.wait_seconds):
            raise AppError(ec.COPILOT_BUSY)
        try:
            yield
        finally:
            self.semaphore.release()
