"""AT-MOTIF-05: transactions just outside each window produce no motif; segments never merge across windows."""

from tests.motifutil import expected, run


def test_AT_MOTIF_05_outside_window() -> None:
    assert run("outside_window") == expected("outside_window") == []


def test_AT_MOTIF_05_no_merge_across_segments() -> None:
    found = run("fan_segmentation")
    assert [f["txs"] for f in found] == [["t1", "t2", "t3"], ["t4", "t5", "t6"]]  # t7 never joins a segment
