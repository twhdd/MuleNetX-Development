"""Direct database seeding for tests that precede or bypass ingestion."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from mulenetx.core.runtime import Runtime
from mulenetx.core.timeutil import utcnow
from mulenetx.db.models.canonical import Account, Transaction
from mulenetx.db.models.datasets import Dataset
from mulenetx.db.models.pipeline import IngestionRun

ANCHOR = datetime(2020, 1, 1, tzinfo=UTC)


@dataclass
class SeededDataset:
    dataset_id: uuid.UUID
    dataset_key: str
    ingestion_run_id: uuid.UUID


def seed_dataset(
    rt: Runtime,
    edges: list[tuple[str, str, float, int]],
    key: str = "fx",
    fraud: set[int] | None = None,
    unlabelled: set[int] | None = None,
    types: list[str] | None = None,
) -> SeededDataset:
    """edges: (source_ref, destination_ref, amount, step). Creates a SUCCEEDED ingestion of these rows."""
    dataset_id, ingestion_id = uuid.uuid4(), uuid.uuid4()
    now = utcnow()
    with rt.session_factory() as db:
        db.add(
            Dataset(
                dataset_id=dataset_id,
                dataset_key=key,
                name=f"fixture {key}",
                source="test",
                dataset_version="v1",
                schema_version="paysim-1",
                adapter="paysim-v1",
                adapter_config={"epoch_anchor": ANCHOR.isoformat()},
                checksum=hashlib.sha256(key.encode()).hexdigest(),
                timestamp_resolution_seconds=3600,
                is_synthetic_injection=False,
                record_count=len(edges),
                created_at=now,
            )
        )
        db.add(
            IngestionRun(
                ingestion_run_id=ingestion_id,
                dataset_id=dataset_id,
                pipeline_version="test",
                started_at=now,
                completed_at=now,
                status="SUCCEEDED",
                records_seen=len(edges),
                records_accepted=len(edges),
                records_rejected=0,
                records_duplicate=0,
                rejection_summary={"counts": {}, "samples": {}},
            )
        )
        db.flush()
        refs = sorted({r for e in edges for r in e[:2]})
        for ref in refs:
            db.add(
                Account(
                    account_id=f"{key}:{ref}",
                    dataset_id=dataset_id,
                    source_account_ref=ref,
                    account_type="MERCHANT" if ref.startswith("M") else "CUSTOMER",
                )
            )
        db.flush()
        for i, (src, dst, amount, step) in enumerate(edges, start=1):
            ref = f"{i:010d}"
            db.add(
                Transaction(
                    transaction_id=f"{key}:{ref}",
                    dataset_id=dataset_id,
                    ingestion_run_id=ingestion_id,
                    source_transaction_ref=ref,
                    source_account_id=f"{key}:{src}",
                    destination_account_id=f"{key}:{dst}",
                    amount=Decimal(str(amount)),
                    timestamp=ANCHOR + timedelta(hours=step),
                    transaction_type="TRANSFER" if types is None else types[i - 1],
                    fraud_label=None if i in (unlabelled or set()) else (i in (fraud or set())),
                    source_record_hash=hashlib.sha256(ref.encode()).hexdigest(),
                )
            )
        db.commit()
    return SeededDataset(dataset_id, key, ingestion_id)
