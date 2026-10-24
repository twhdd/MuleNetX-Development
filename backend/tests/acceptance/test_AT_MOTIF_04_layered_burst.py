"""AT-MOTIF-04: layered movement and burst activity (known 168-bucket baseline) with deterministic confidence."""

from tests.motifutil import expected, run


def test_AT_MOTIF_04_layered() -> None:
    assert run("layered") == expected("layered")


def test_AT_MOTIF_04_burst_against_baseline() -> None:
    first = run("burst")
    assert first == expected("burst")
    assert run("burst") == first  # deterministic
