"""A stopped Compose service has no DNS entry; the driver then raises ValueError("Cannot resolve address ...").
That must read as GRAPH_UNAVAILABLE (AT-OPS-02), while any other ValueError still propagates."""

import pytest

from mulenetx.core.errors import AppError
from mulenetx.graph.neo4j_client import Neo4jClient, is_unreachable


class _Driver:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def verify_connectivity(self) -> None:
        raise self.exc

    def session(self):  # type: ignore[no-untyped-def]
        raise self.exc

    def close(self) -> None:
        pass


def _client(exc: Exception) -> Neo4jClient:
    c = Neo4jClient("bolt://neo4j:7687", "neo4j", "x")
    c._driver = _Driver(exc)  # type: ignore[assignment]
    return c


def test_unresolvable_host_is_unavailable() -> None:
    exc = ValueError("Cannot resolve address neo4j:7687")
    assert is_unreachable(exc)
    c = _client(exc)
    assert c.ping() is False
    with pytest.raises(AppError) as err:
        c.run("RETURN 1")
    assert err.value.code == "GRAPH_UNAVAILABLE"
    with pytest.raises(AppError), c.session():
        pass


def test_other_value_errors_propagate() -> None:
    c = _client(ValueError("bad parameter"))
    assert not is_unreachable(ValueError("bad parameter"))
    with pytest.raises(ValueError, match="bad parameter"):
        c.ping()
    with pytest.raises(ValueError, match="bad parameter"):
        c.run("RETURN 1")
