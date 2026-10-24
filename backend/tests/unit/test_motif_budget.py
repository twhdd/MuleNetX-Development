"""The per-anchor expansion budget stops enumeration deterministically and marks the instances truncated."""

from mulenetx.motifs.common import Index, MTx
from mulenetx.motifs.paths import detect_path_motifs


def _star() -> list[MTx]:
    # A fans out to B0..B9 at t=0; each Bi passes on to Ci within 60 s
    txs = [MTx(0, f"a{i}", "A", f"B{i}") for i in range(10)]
    txs += [MTx(60, f"b{i}", f"B{i}", f"C{i}") for i in range(10)]
    return txs


def test_budget_truncates_deterministically() -> None:
    full = detect_path_motifs(Index(_star()), 5, 100_000)
    assert len([m for m in full if m.anchor == "A"]) == 10 and not any(m.truncated for m in full)
    small = detect_path_motifs(Index(_star()), 5, 6)
    again = detect_path_motifs(Index(_star()), 5, 6)
    from_a = [m for m in small if m.anchor == "A"]
    assert 0 < len(from_a) < 10 and all(m.truncated for m in from_a)
    assert [m.tx_ids for m in small] == [m.tx_ids for m in again]
