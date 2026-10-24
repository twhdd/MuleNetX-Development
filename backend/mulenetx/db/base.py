"""Declarative base. Tables are created by Alembic migrations, never by `create_all`."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, DOUBLE_PRECISION, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    type_annotation_map = {
        UUID: PG_UUID(as_uuid=True),
        datetime: DateTime(timezone=True),
        Decimal: Numeric(),
        dict[str, Any]: JSONB(),
        list[Any]: JSONB(),
        str: Text(),
        int: Integer(),
        bool: Boolean(),
    }


# Re-exported column type helpers used by the model modules.
__all__ = [
    "ARRAY",
    "DOUBLE_PRECISION",
    "JSONB",
    "BigInteger",
    "Base",
    "Integer",
    "Numeric",
    "SmallInteger",
    "String",
    "Text",
]
