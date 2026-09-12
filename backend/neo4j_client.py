from neo4j import GraphDatabase
from backend.config import settings
from backend.core.query_guard import (
    validate_query
)


class QueryResult:
    def __init__(self, records):
        self._records = records

    def single(self):
        return self._records[0] if self._records else None

    def __iter__(self):
        return iter(self._records)

    def __len__(self):
        return len(self._records)


class Neo4jClient:
    def __init__(self, uri=None, username=None, password=None):
        self.uri = uri or settings.neo4j_uri
        self.username = username or settings.neo4j_username
        self.password = password or settings.neo4j_password
        self._driver = None

    @property
    def driver(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
        return self._driver

    def execute(
        self,
        query,
        parameters=None
    ):
        validate_query(query)

        with self.driver.session() as session:
            result = session.run(
                query,
                parameters or {}
            )
            return QueryResult(list(result))

    def execute_admin(
        self,
        query,
        parameters=None
    ):
        with self.driver.session() as session:
            result = session.run(
                query,
                parameters or {}
            )
            return QueryResult(list(result))

    def close(self):
        if self._driver is not None:
            self._driver.close()


neo4j_client = Neo4jClient()

