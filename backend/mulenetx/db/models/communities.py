"""Communities and memberships (SRS §6.3.5)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class Community(Base):
    __tablename__ = "communities"

    community_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analytics_run_id: Mapped[UUID] = mapped_column(primary_key=True)
    graph_snapshot_id: Mapped[UUID]
    algorithm: Mapped[str] = mapped_column(String(100))
    algorithm_version: Mapped[str] = mapped_column(String(100))
    member_count: Mapped[int]
    computed_at: Mapped[datetime]
    analytical_summary: Mapped[dict[str, Any] | None]


class CommunityMembership(Base):
    __tablename__ = "community_memberships"

    analytics_run_id: Mapped[UUID] = mapped_column(primary_key=True)
    community_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    membership_score: Mapped[Decimal | None] = mapped_column(Numeric(12, 8))
