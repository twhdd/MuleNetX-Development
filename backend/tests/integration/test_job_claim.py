"""Two (or more) workers never claim the same job (SRS §7.8, SKIP LOCKED)."""

import threading

import pytest

from mulenetx.jobs import queue
from tests import jobutil

pytestmark = pytest.mark.integration


def test_concurrent_claims_are_disjoint(clean_db: str) -> None:
    rt = jobutil.runtime(clean_db)
    ids = jobutil.enqueue(rt, n=60)
    claimed: dict[str, list] = {}
    barrier = threading.Barrier(4)

    def worker(name: str) -> None:
        got = []
        barrier.wait()
        while True:
            with rt.engine.connect() as conn:
                job = queue.claim(conn, name, ("SNAPSHOT_RETIRE",), 60)
            if job is None:
                break
            got.append(job.job_id)
        claimed[name] = got

    threads = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    flat = [j for got in claimed.values() for j in got]
    assert sorted(flat) == sorted(ids)
    assert len(flat) == len(set(flat))
    row = jobutil.job_row(rt, ids[0])
    assert row.status == "RUNNING" and row.attempts == 1 and row.lease_owner.startswith("w")
    rt.close()


def test_claim_order_is_fifo(clean_db: str) -> None:
    rt = jobutil.runtime(clean_db)
    ids = jobutil.enqueue(rt, n=3)
    with rt.engine.connect() as conn:
        got = [queue.claim(conn, "w", ("SNAPSHOT_RETIRE",), 60) for _ in range(3)]
    assert [g.job_id for g in got if g] == ids
    rt.close()


def test_claim_respects_kinds(clean_db: str) -> None:
    rt = jobutil.runtime(clean_db)
    jobutil.enqueue(rt, kind="EVALUATION")
    with rt.engine.connect() as conn:
        assert queue.claim(conn, "w", ("SNAPSHOT_RETIRE",), 60) is None
        assert queue.claim(conn, "w", ("EVALUATION",), 60) is not None
    rt.close()
