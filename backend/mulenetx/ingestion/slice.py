"""PaySim reference slice (SRS §7.1.2): all rows with step ≤ S*, where S* is the largest step such that the
number of rows with step ≤ S* is at most `reference_slice_max_rows`."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from mulenetx.ingestion.staging import file_checksum


def compute_s_star(step_counts: dict[int, int], max_rows: int) -> int | None:
    """Largest step S with cumulative count(step ≤ S) ≤ max_rows; None if even the first step exceeds it."""
    s_star: int | None = None
    cumulative = 0
    for step in sorted(step_counts):
        cumulative += step_counts[step]
        if cumulative > max_rows:
            break
        s_star = step
    return s_star


def _step(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    return int(text) if text.isdigit() else None


def count_steps(source: Path) -> Counter[int]:
    counts: Counter[int] = Counter()
    with source.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            step = _step(row.get("step"))
            if step is not None:
                counts[step] += 1
    return counts


def make_slice(source: Path, destination: Path, max_rows: int) -> dict[str, Any]:
    """Write the slice CSV (original row order and header) and return the adapter_config entries to record."""
    counts = count_steps(source)
    s_star = compute_s_star(dict(counts), max_rows)
    if s_star is None:
        raise ValueError("the first step alone exceeds reference_slice_max_rows")
    written = 0
    with (
        source.open("r", encoding="utf-8", newline="") as src,
        destination.open("w", encoding="utf-8", newline="") as dst,
    ):
        reader = csv.reader(src)
        writer = csv.writer(dst, lineterminator="\n")
        header = next(reader)
        writer.writerow(header)
        step_index = header.index("step")
        for row in reader:
            step = _step(row[step_index]) if step_index < len(row) else None
            if step is not None and step <= s_star:
                writer.writerow(row)
                written += 1
    source_checksum, _ = file_checksum(source)
    return {
        "slice_rule": "step <= S*",
        "s_star": s_star,
        "reference_slice_max_rows": max_rows,
        "slice_row_count": written,
        "source_file_checksum": source_checksum,
    }
