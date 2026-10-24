"""Cases, case subjects and findings (SRS §6.3.8)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from mulenetx.db.base import Base


class Case(Base):
    __tablename__ = "cases"

    case_id: Mapped[UUID] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(250))
    status: Mapped[str] = mapped_column(String(30))
    priority: Mapped[str] = mapped_column(String(20))
    assigned_to: Mapped[UUID | None]
    created_by: Mapped[UUID]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    closed_at: Mapped[datetime | None]
    version: Mapped[int]


class CaseSubject(Base):
    __tablename__ = "case_subjects"

    case_id: Mapped[UUID] = mapped_column(primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(20), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    added_by: Mapped[UUID]
    added_at: Mapped[datetime] = mapped_column(primary_key=True)
    removed_by: Mapped[UUID | None]
    removed_at: Mapped[datetime | None]


class Finding(Base):
    __tablename__ = "findings"

    finding_id: Mapped[UUID] = mapped_column(primary_key=True)
    case_id: Mapped[UUID]
    type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str]
    evidence: Mapped[list[Any]]
    source: Mapped[str] = mapped_column(String(100))
    created_by: Mapped[UUID]
    created_at: Mapped[datetime]
