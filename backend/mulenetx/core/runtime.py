"""Process-wide runtime resources shared by the API and the worker (engine, sessions, graph client)."""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from mulenetx.core.config import Settings
from mulenetx.db.engine import make_engine
from mulenetx.db.session import make_session_factory
from mulenetx.graph.neo4j_client import Neo4jClient


@dataclass
class Runtime:
    settings: Settings
    _engine: Engine | None = field(default=None, init=False)
    _factory: sessionmaker[Session] | None = field(default=None, init=False)
    _graph: Neo4jClient | None = field(default=None, init=False)

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = make_engine(self.settings.postgres_dsn)
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        if self._factory is None:
            self._factory = make_session_factory(self.engine)
        return self._factory

    @property
    def graph(self) -> Neo4jClient:
        if self._graph is None:
            self._graph = Neo4jClient(self.settings.neo4j_uri, self.settings.neo4j_user, self.settings.neo4j_password)
        return self._graph

    def close(self) -> None:
        if self._graph is not None:
            self._graph.close()
        if self._engine is not None:
            self._engine.dispose()
