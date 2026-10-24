from mulenetx.motifs.common import Index, MTx
from mulenetx.motifs.fan import detect_fans


def test_parallel_transactions_count_one_counterparty_and_keep_the_earliest() -> None:
    txs = [MTx(0, "t1", "A", "D"), MTx(10, "t2", "A", "D"), MTx(20, "t3", "B", "D"), MTx(30, "t4", "C", "D")]
    (inst,) = detect_fans(Index(txs))
    assert inst.motif_type == "FAN_IN" and [t.transaction_id for t in inst.transactions] == ["t1", "t3", "t4"]


def test_two_counterparties_do_not_fan_and_self_transfers_are_ignored() -> None:
    txs = [MTx(0, "t1", "A", "D"), MTx(1, "t2", "B", "D"), MTx(2, "t3", "D", "D")]
    assert detect_fans(Index(txs)) == []
