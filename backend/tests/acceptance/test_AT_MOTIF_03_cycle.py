"""AT-MOTIF-03: a circular flow is identified with its exact confidence, and its evidence makes no criminality
claim (SRS §15.9.4: cycle existence alone is not proof of suspiciousness)."""

from datetime import UTC, datetime

from mulenetx.motifs.service import detect, to_row
from tests.conftest import make_settings
from tests.flowutil import RUN, SNAPSHOT
from tests.motifutil import expected, run, transactions


def test_AT_MOTIF_03_cycle() -> None:
    assert run("cycle") == expected("cycle")
    (inst,) = detect(transactions("cycle"), make_settings())
    row = to_row(inst, SNAPSHOT, RUN, "nx-test", datetime(2026, 1, 1, tzinfo=UTC))
    evidence = row[13]
    assert evidence["statement"] == "A motif is an analytical pattern, not a criminality classification."
    text = str(evidence).lower()
    for word in ("fraud", "launder", "criminal ", "mule account", "guilty"):
        assert word not in text
