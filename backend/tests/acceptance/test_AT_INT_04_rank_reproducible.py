"""AT-INT-04 (and §27.10 checks 7–8): ranking twice, and under CPU load, gives identical order and candidate IDs."""

import threading

from tests.interventionutil import counterexample_baseline, rank


def _burn(stop: threading.Event) -> None:
    x = 1
    while not stop.is_set():
        x = (x * 48271) % 2147483647


def test_AT_INT_04_rank_reproducible() -> None:
    first = [(r.candidate_id, r.rank_position, r.intervention_score) for r in rank(counterexample_baseline())]
    assert [p for _c, p, _s in first] == list(range(1, len(first) + 1))
    assert len({c for c, _p, _s in first}) == len(first)
    stop = threading.Event()
    burners = [threading.Thread(target=_burn, args=(stop,)) for _ in range(4)]
    for t in burners:
        t.start()
    try:
        again = [
            [(r.candidate_id, r.rank_position, r.intervention_score) for r in rank(counterexample_baseline())]
            for _ in range(3)
        ]
    finally:
        stop.set()
        for t in burners:
            t.join()
    assert all(a == first for a in again)
