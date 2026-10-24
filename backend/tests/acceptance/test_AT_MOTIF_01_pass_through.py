"""AT-MOTIF-01: rapid pass-through A→B→C→D: the expected maximal sequence, exact confidence and evidence."""

from mulenetx.motifs.service import detect
from tests.conftest import make_settings
from tests.motifutil import expected, run, transactions


def test_AT_MOTIF_01_pass_through() -> None:
    assert run("pass_through") == expected("pass_through")
    (inst,) = detect(transactions("pass_through"), make_settings())
    assert inst.accounts == ["A", "B", "C", "D"] and inst.window_seconds == 900
    assert inst.components["structural_match"] == "1.0000000" and inst.components["participant_match"] == "1.0000000"
    assert inst.start == 0 and inst.end == 900 and inst.truncated is False


def test_AT_MOTIF_01_equal_timestamps_and_parallel() -> None:
    assert run("equal_timestamps") == expected("equal_timestamps")
    assert run("parallel") == expected("parallel")
