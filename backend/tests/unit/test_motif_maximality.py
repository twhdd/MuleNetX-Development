from mulenetx.motifs.common import maximal


def test_contiguous_subsequences_are_dropped() -> None:
    seqs = [("t1", "t2"), ("t2", "t3"), ("t1", "t2", "t3"), ("t1", "t3")]
    assert maximal(seqs) == {("t1", "t2", "t3"), ("t1", "t3")}  # (t1, t3) is not contiguous in (t1, t2, t3)


def test_duplicates_and_singletons() -> None:
    assert maximal([("a", "b"), ("a", "b")]) == {("a", "b")}
    assert maximal([]) == set()
