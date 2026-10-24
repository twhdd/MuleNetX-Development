"""Canonical accounts and transactions (SRS §6.3.2)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CHAR, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    dataset_id: Mapped[UUID]
    source_account_ref: Mapped[str] = mapped_column(String(128))
    account_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime | None]
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 7))
    risk_tier: Mapped[str | None] = mapped_column(String(20))
    community_id: Mapped[str | None] = mapped_column(String(64))
    latest_risk_assessment_id: Mapped[UUID | None]


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    dataset_id: Mapped[UUID]
    ingestion_run_id: Mapped[UUID]
    source_transaction_ref: Mapped[str] = mapped_column(String(128))
    source_account_id: Mapped[str] = mapped_column(String(160))
    destination_account_id: Mapped[str] = mapped_column(String(160))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    timestamp: Mapped[datetime]
    transaction_type: Mapped[str] = mapped_column(String(50))
    fraud_label: Mapped[bool | None]
    source_record_hash: Mapped[str] = mapped_column(CHAR(64))
