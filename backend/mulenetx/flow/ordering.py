"""Path ordering (SRS §16.5): length ascending; total supporting amount descending (sum of hop totals);
lexicographic account-ID sequence; lexicographic sequence of each hop's first supporting transaction ID."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

Edge = tuple[str, str]


def path_sort_key(
    accounts: Sequence[str], hop_micros: Mapping[Edge, int], first_tx: Mapping[Edge, str]
) -> tuple[int, int, tuple[str, ...], tuple[str, ...]]:
    hops = list(zip(accounts, accounts[1:], strict=False))
    total = sum(hop_micros[h] for h in hops)
    return (len(hops), -total, tuple(accounts), tuple(first_tx.get(h, "") for h in hops))
