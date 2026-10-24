"""AT-MOTIF-02: fan-in and fan-out topology, inclusive 3600 s window, greedy non-overlapping segmentation."""

from tests.motifutil import expected, run


def test_AT_MOTIF_02_fan_in() -> None:
    assert run("fan_in") == expected("fan_in")


def test_AT_MOTIF_02_fan_out_inclusive_window() -> None:
    assert run("fan_out") == expected("fan_out")


def test_AT_MOTIF_02_greedy_segmentation() -> None:
    assert run("fan_segmentation") == expected("fan_segmentation")
