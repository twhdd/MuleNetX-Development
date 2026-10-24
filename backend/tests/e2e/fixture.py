"""The golden-path dataset as a PaySim CSV: the synthetic labelled dataset (tests/synth.py) plus a dense
six-account cluster in the test window, so a potential fraud ring candidate exists (as tests/evalutil.py).

    uv run python -m tests.e2e.fixture <path.csv>     # used by `make test-e2e` for the Playwright run
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from tests.synth import generate

HEADER = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
]


def write_fixture(path: Path) -> int:
    edges, fraud, types = generate(customers=300, mules=30, steps=60, seed=11)
    ring = [f"R{i}" for i in range(6)]
    for step in (56, 57, 58, 59):
        for i in range(6):
            for offset, amount in ((1, 9000.0), (2, 7000.0)):
                fraud.add(len(edges))
                edges.append((ring[i], ring[(i + offset) % 6], amount + i, step))
                types.append("TRANSFER")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for i, (src, dst, amount, step) in enumerate(edges):
            w.writerow(
                [step, types[i], f"{amount:.2f}", src, "0.00", "0.00", dst, "0.00", "0.00", 1 if i in fraud else 0, 0]
            )
    return len(edges)


if __name__ == "__main__":
    print(write_fixture(Path(sys.argv[1])))  # noqa: T201
