"""Datasets (SRS §6.3.2) and dataset profiles (§6.3.3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CHAR, BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class Dataset(Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[UUID] = mapped_column(primary_key=True)
    dataset_key: Mapped[str] = mapped_column(String(24))
    name: Mapped[str] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(100))
    dataset_version: Mapped[str] = mapped_column(String(100))
    schema_version: Mapped[str] = mapped_column(String(50))
    adapter: Mapped[str] = mapped_column(String(50))
    adapter_config: Mapped[dict[str, Any]]
    checksum: Mapped[str] = mapped_column(CHAR(64))
    timestamp_resolution_seconds: Mapped[int]
    is_synthetic_injection: Mapped[bool]
    record_count: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime]


class DatasetProfile(Base):
    __tablename__ = "dataset_profiles"

    dataset_id: Mapped[UUID] = mapped_column(primary_key=True)
    profile_version: Mapped[str] = mapped_column(String(50))
    metrics: Mapped[dict[str, Any]]
    created_at: Mapped[datetime]
