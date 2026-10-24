"""Neo4j driver wrapper (SRS §6.8). Only GraphService and AnalyticsService use it (§4.2)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from neo4j import Driver, GraphDatabase, Query, Session
from neo4j.exceptions import DriverError, Neo4jError, ServiceUnavailable

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError

logger = logging.getLogger("mulenetx.graph")

# Constraints and indexes of SRS §6.8.1, plus Transaction(snapshot_id) used by batched retirement deletes.
SCHEMA_STATEMENTS = (
    "CREATE CONSTRAINT account_snapshot_key IF NOT EXISTS FOR (a:Account) REQUIRE a.snapshot_key IS UNIQUE",
    "CREATE CONSTRAINT transaction_snapshot_key IF NOT EXISTS FOR (t:Transaction) REQUIRE t.snapshot_key IS UNIQUE",
    "CREATE INDEX account_account_id IF NOT EXISTS FOR (a:Account) ON (a.account_id)",
    "CREATE INDEX account_snapshot_id IF NOT EXISTS FOR (a:Account) ON (a.snapshot_id)",
    "CREATE INDEX transaction_transaction_id IF NOT EXISTS FOR (t:Transaction) ON (t.transaction_id)",
    "CREATE INDEX transaction_snapshot_id IF NOT EXISTS FOR (t:Transaction) ON (t.snapshot_id)",
)

GRAPH_ERRORS: tuple[type[Exception], ...] = (ServiceUnavailable, DriverError, OSError)
# also caught, then narrowed by is_unreachable(): the driver's name-resolution failure is a ValueError
CONNECT_ERRORS: tuple[type[Exception], ...] = (*GRAPH_ERRORS, ValueError)


def is_unreachable(exc: BaseException) -> bool:
    """Connection failures, including the driver's ValueError when the host name does not resolve (a stopped
    Compose service has no DNS entry). Any other ValueError is a programming error and must propagate."""
    if isinstance(exc, GRAPH_ERRORS):
        return True
    return isinstance(exc, ValueError) and "resolve address" in str(exc)


class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str, *, connection_timeout: float = 5.0) -> None:
        self._uri = uri
        self._auth = (user, password)
        self._timeout = connection_timeout
        self._driver: Driver | None = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=self._auth,
                connection_timeout=self._timeout,
                max_connection_lifetime=300,
                connection_acquisition_timeout=self._timeout,
            )
        return self._driver

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def ping(self) -> bool:
        try:
            self.driver.verify_connectivity()
        except (ServiceUnavailable, DriverError, OSError, Neo4jError):
            return False
        except ValueError as exc:
            if is_unreachable(exc):
                return False
            raise
        return True

    @contextmanager
    def session(self) -> Iterator[Session]:
        try:
            with self.driver.session() as s:
                yield s
        except CONNECT_ERRORS as exc:
            if not is_unreachable(exc):
                raise
            logger.warning("neo4j unavailable: %s", type(exc).__name__)
            raise AppError(ec.GRAPH_UNAVAILABLE) from exc

    def run(
        self, query: str, parameters: dict[str, Any] | None = None, *, timeout: float | None = None
    ) -> list[dict[str, Any]]:
        """Run one parameterized read/write query in an auto-commit transaction and return records as dicts."""
        try:
            with self.driver.session() as s:
                result = s.run(Query(query, timeout=timeout), parameters or {})
                return [record.data() for record in result]
        except CONNECT_ERRORS as exc:
            if not is_unreachable(exc):
                raise
            logger.warning("neo4j unavailable: %s", type(exc).__name__)
            raise AppError(ec.GRAPH_UNAVAILABLE) from exc

    def create_schema(self) -> None:
        for stmt in SCHEMA_STATEMENTS:
            self.run(stmt)
