"""Deterministic synthetic PaySim-like data with labelled fraud, for ML, scoring and ring tests.

Normal customers pay merchants and transfer to each other; fraud victims receive a fraud-labelled TRANSFER
into a mule which cashes out within the hour. Fraud appears throughout the timeline so every split has
positives.
"""

from __future__ import annotations

import random
from pathlib import Path

Edge = tuple[str, str, float, int]
HEADER = (
    "step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,"
    "isFraud,isFlaggedFraud\n"
)


def generate(
    customers: int = 300, mules: int = 30, steps: int = 60, seed: int = 11
) -> tuple[list[Edge], set[int], list[str]]:
    """Customers join in cohorts across the timeline (so every chronological split has new accounts); every
    other step one victim sends a fraud-labelled TRANSFER to a mule that cashes out in the same hour."""
    rng = random.Random(seed)
    edges: list[Edge] = []
    types: list[str] = []
    fraud: set[int] = set()
    merchants = [f"M{i:04d}" for i in range(20)]
    start = {f"C{i:05d}": (i * steps) // customers for i in range(customers)}
    cust = sorted(start)
    mule_ids = [f"C9{i:04d}" for i in range(mules)]
    for step in range(steps):
        active = [c for c in cust if start[c] <= step]
        newcomers = [c for c in cust if start[c] == step]
        for a in newcomers + [rng.choice(active) for _ in range(max(4, len(active) // 8))]:
            if rng.random() < 0.6:
                edges.append((a, rng.choice(merchants), round(rng.uniform(5, 300), 2), step))
                types.append("PAYMENT")
            else:
                b = rng.choice(active)
                if b != a:
                    edges.append((a, b, round(rng.uniform(10, 2000), 2), step))
                    types.append("TRANSFER")
        if step % 2 == 0:
            m = mule_ids[(step // 2) % mules]
            victim = rng.choice(active)
            amount = round(rng.uniform(5000, 50000), 2)
            edges.append((victim, m, amount, step))
            types.append("TRANSFER")
            fraud.add(len(edges))
            edges.append((m, rng.choice(active), amount, step))
            types.append("CASH_OUT")
            fraud.add(len(edges))
    return edges, fraud, types


def write_csv(path: Path, edges: list[Edge], fraud: set[int], types: list[str]) -> Path:
    with path.open("w") as f:
        f.write(HEADER)
        for i, ((src, dst, amount, step), tx_type) in enumerate(zip(edges, types, strict=True), start=1):
            f.write(f"{step},{tx_type},{amount:.2f},{src},0,0,{dst},0,0,{1 if i in fraud else 0},0\n")
    return path
