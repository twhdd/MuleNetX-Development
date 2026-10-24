"""AT-DATA-05: a large upload (200 MB) is accepted with 202 within 30 s; ingestion proceeds in the worker."""

import time
from pathlib import Path

import pytest
from sqlalchemy import text

from mulenetx.api.deps import get_services
from tests.apiutil import _Req
from tests.ingestutil import upload

pytestmark = pytest.mark.integration

HEADER = (
    "step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,"
    "isFraud,isFlaggedFraud\n"
)


def _generate(path: Path, target_bytes: int) -> int:
    line = "1,TRANSFER,181.000000,C1231006815,181.0,0.0,C1666544295,0.0,0.0,1,0\n"
    block = line * 10_000
    written = 0
    with path.open("w") as f:
        f.write(HEADER)
        while written < target_bytes:
            f.write(block)
            written += len(block)
    return path.stat().st_size


def test_AT_DATA_05_large_upload_accepted_quickly(app, client, users, tmp_path: Path) -> None:
    admin = users("ADMIN")
    big = tmp_path / "large.csv"
    size = _generate(big, 200 * 1024 * 1024)
    assert size >= 200 * 1024 * 1024
    started = time.monotonic()
    resp = upload(client, admin, big, name="large upload")
    elapsed = time.monotonic() - started
    assert resp.status_code == 202, resp.text
    assert elapsed < 30, f"202 took {elapsed:.1f} s"
    rt = get_services(_Req(app)).runtime
    with rt.engine.connect() as conn:
        job = conn.execute(
            text("SELECT kind, status FROM jobs WHERE payload->>'ingestion_run_id' = :i"),
            {"i": resp.json()["ingestion_run_id"]},
        ).one()
    assert (job.kind, job.status) == ("INGEST", "QUEUED")  # parsing happens in the worker, not the request
    big.unlink()
    with rt.engine.connect() as conn:
        staged = conn.execute(
            text("SELECT payload->>'staged_path' FROM jobs WHERE payload->>'ingestion_run_id' = :i"),
            {"i": resp.json()["ingestion_run_id"]},
        ).scalar_one()
    Path(staged).unlink(missing_ok=True)
