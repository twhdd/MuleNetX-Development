"""Unpublished ports are unreachable from the host (SR-22, SRS §27.6): with the Compose stack up, only the
dashboard and backend accept connections; PostgreSQL, Neo4j (Bolt and HTTP) and Ollama do not."""

from __future__ import annotations

import socket
import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.docker]

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ["docker", "compose", "-f", str(ROOT / "docker-compose.yml"), "--project-directory", str(ROOT)]
CLOSED = {"postgres": 5432, "neo4j-bolt": 7687, "neo4j-http": 7474, "ollama": 11434}
OPEN = {"backend": 8000, "dashboard": 8080}


def reachable(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def test_only_published_ports_are_reachable() -> None:
    if not (ROOT / ".env").exists():
        pytest.fail("the Compose stack needs .env at the repository root")
    up = subprocess.run(
        [*COMPOSE, "up", "-d", "--wait", "backend", "dashboard", "ollama"],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert up.returncode == 0, up.stderr[-2000:]
    for name, port in OPEN.items():
        assert reachable(port), f"{name} should be published on {port}"
    for name, port in CLOSED.items():
        assert not reachable(port), f"{name} must not be reachable from the host on {port}"
