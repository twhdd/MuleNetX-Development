"""Ring membership and constituent transactions (SRS §9A.2): members are all members of the source community;
constituent transactions are the snapshot transactions whose source and destination are both members."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mulenetx.flow.analytic_paths import Tx
from mulenetx.rings.inputs import ContextInputs


@dataclass(frozen=True)
class Membership:
    members: list[str]  # account_id order
    constituent: list[tuple[str, str, Tx]]  # (timestamp, transaction_id) order

    @property
    def ring_size(self) -> int:
        return len(self.members)

    @property
    def start_time(self) -> datetime | None:
        return self.constituent[0][2].timestamp if self.constituent else None

    @property
    def end_time(self) -> datetime | None:
        return self.constituent[-1][2].timestamp if self.constituent else None

    @property
    def temporal_span_seconds(self) -> int:
        if not self.constituent:
            return 0
        return int((self.constituent[-1][2].timestamp - self.constituent[0][2].timestamp).total_seconds())


def membership(ctx: ContextInputs, community_members: list[str]) -> Membership:
    members = sorted(set(community_members))
    return Membership(members, ctx.internal(set(members)))
