"""Upload staging (SR-23) and the per-run UNLOGGED staging table (SRS §7.2)."""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import Engine, text

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError
from mulenetx.ingestion.adapters.paysim_v1 import NormalizedRow

CHUNK = 1024 * 1024
STAGING_COLUMNS = (
    "ordinal",
    "source_transaction_ref",
    "source_account_ref",
    "source_account_type",
    "destination_account_ref",
    "destination_account_type",
    "amount",
    "ts",
    "transaction_type",
    "fraud_label",
    "source_record_hash",
)


def stream_to_staging(source: BinaryIO, staging_dir: str, max_bytes: int) -> tuple[Path, str, int]:
    """Copy an upload to the staging volume, computing SHA-256 and enforcing the size cap while streaming."""
    directory = Path(staging_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"upload-{uuid.uuid4().hex}.csv"
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("wb") as out:
            while True:
                chunk = source.read(CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise AppError(ec.PAYLOAD_TOO_LARGE, details={"limit": max_bytes})
                digest.update(chunk)
                out.write(chunk)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    os.chmod(path, 0o440)
    return path, digest.hexdigest(), size


def file_checksum(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        while chunk := f.read(CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def staging_table(ingestion_run_id: uuid.UUID) -> str:
    return f"staging.ingest_{ingestion_run_id.hex}"


def create_staging_table(engine: Engine, ingestion_run_id: uuid.UUID) -> str:
    """Create (or truncate, on retry) the run's UNLOGGED staging table."""
    name = staging_table(ingestion_run_id)
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE UNLOGGED TABLE IF NOT EXISTS {name} ("
                "ordinal BIGINT PRIMARY KEY, source_transaction_ref VARCHAR(128) NOT NULL, "
                "source_account_ref VARCHAR(128) NOT NULL, source_account_type VARCHAR(50) NOT NULL, "
                "destination_account_ref VARCHAR(128) NOT NULL, destination_account_type VARCHAR(50) NOT NULL, "
                "amount NUMERIC(20,6) NOT NULL, ts TIMESTAMPTZ NOT NULL, transaction_type VARCHAR(50) NOT NULL, "
                "fraud_label BOOLEAN, source_record_hash CHAR(64) NOT NULL)"
            )
        )
        conn.execute(text(f"TRUNCATE {name}"))
    return name


def copy_rows(engine: Engine, table: str, rows: list[NormalizedRow]) -> None:
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        columns = ", ".join(STAGING_COLUMNS)
        with cursor.copy(f"COPY {table} ({columns}) FROM STDIN") as copy:
            for r in rows:
                copy.write_row(
                    (
                        r.ordinal,
                        r.source_transaction_ref,
                        r.source_account_ref,
                        r.source_account_type,
                        r.destination_account_ref,
                        r.destination_account_type,
                        r.amount,
                        r.timestamp,
                        r.transaction_type,
                        r.fraud_label,
                        r.source_record_hash,
                    )
                )
        raw.commit()
    finally:
        raw.close()


def drop_staging_table(engine: Engine, ingestion_run_id: uuid.UUID) -> None:
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {staging_table(ingestion_run_id)}"))
