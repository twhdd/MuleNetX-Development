from mulenetx.motifs.common import MTx, order_ambiguous_path


def test_equal_consecutive_timestamps_are_ambiguous() -> None:
    assert order_ambiguous_path([MTx(5, "a", "A", "B"), MTx(5, "b", "B", "C")])
    assert not order_ambiguous_path([MTx(5, "a", "A", "B"), MTx(6, "b", "B", "C")])
    # only consecutive hops matter
    assert not order_ambiguous_path([MTx(5, "a", "A", "B"), MTx(6, "b", "B", "C"), MTx(7, "c", "C", "D")])
