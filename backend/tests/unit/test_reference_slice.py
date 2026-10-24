"""PaySim reference slice (SRS §7.1.2)."""

from pathlib import Path

from mulenetx.ingestion.slice import compute_s_star, make_slice


def test_s_star_largest_step_within_limit() -> None:
    counts = {1: 3, 2: 4, 3: 5}
    assert compute_s_star(counts, 7) == 2
    assert compute_s_star(counts, 6) == 1
    assert compute_s_star(counts, 12) == 3
    assert compute_s_star(counts, 2) is None


def test_s_star_with_gaps_and_unordered_steps() -> None:
    assert compute_s_star({10: 1, 1: 1, 5: 1}, 2) == 5


def test_make_slice_keeps_order_and_records_config(tmp_path: Path) -> None:
    src = tmp_path / "src.csv"
    src.write_text("step,type,amount\n2,T,1\n1,T,2\n3,T,3\n1,T,4\n2,T,5\n")
    dst = tmp_path / "slice.csv"
    cfg = make_slice(src, dst, 4)
    assert dst.read_text() == "step,type,amount\n2,T,1\n1,T,2\n1,T,4\n2,T,5\n"
    assert cfg["s_star"] == 2 and cfg["slice_row_count"] == 4 and cfg["reference_slice_max_rows"] == 4
    assert cfg["slice_rule"] == "step <= S*" and len(cfg["source_file_checksum"]) == 64
