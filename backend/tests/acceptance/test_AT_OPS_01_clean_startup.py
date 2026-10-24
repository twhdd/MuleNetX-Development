"""AT-OPS-01: from the Compose file, migrate completes, health and readiness succeed, and only the
dashboard and backend publish ports (SR-22). Drives the real stack; requires `.env` at the repo root."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import httpx
import pytest

pytestmark = [pytest.mark.docker]

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ["docker", "compose", "-f", str(ROOT / "docker-compose.yml"), "--project-directory", str(ROOT)]
PUBLISHED_ALLOWED = {"dashboard", "backend"}


def _compose(*args: str, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run([*COMPOSE, *args], capture_output=True, text=True, timeout=timeout, check=False)


def _wait_ready(url: str, deadline_s: float = 300) -> httpx.Response:
    end = time.monotonic() + deadline_s
    last: httpx.Response | None = None
    while time.monotonic() < end:
        try:
            last = httpx.get(url, timeout=5)
            if last.status_code == 200:
                return last
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise AssertionError(f"not ready: {last.text if last else 'no response'}")


def test_AT_OPS_01_clean_startup() -> None:
    up = _compose("up", "--build", "-d")
    assert up.returncode == 0, up.stderr[-2000:]

    ready = _wait_ready("http://127.0.0.1:8000/ready")
    assert ready.json()["components"]["postgres"] == "UP"
    assert httpx.get("http://127.0.0.1:8000/health", timeout=5).status_code == 200
    assert httpx.get("http://127.0.0.1:8080/health", timeout=5).status_code == 200

    ps = _compose("ps", "--all", "--format", "json")
    assert ps.returncode == 0, ps.stderr
    services = [json.loads(line) for line in ps.stdout.splitlines() if line.strip()]
    by_name = {s["Service"]: s for s in services}
    migrate = by_name["migrate"]
    assert migrate["State"] == "exited" and migrate["ExitCode"] == 0, migrate

    for svc in services:
        published = [p for p in svc.get("Publishers") or [] if p.get("PublishedPort")]
        if svc["Service"] in PUBLISHED_ALLOWED:
            assert published, f"{svc['Service']} should publish a port"
        else:
            assert not published, f"{svc['Service']} publishes {published}"
    for name in ("postgres", "neo4j", "ollama", "worker"):
        port = _compose("port", name, {"postgres": "5432", "neo4j": "7687", "ollama": "11434", "worker": "8000"}[name])
        # `docker compose port` prints ":0" (or fails) for an unpublished port.
        assert port.returncode != 0 or port.stdout.strip() in ("", ":0"), f"{name} port published: {port.stdout}"
