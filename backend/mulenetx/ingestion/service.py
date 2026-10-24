"""IngestionService (SRS §7.1–§7.5, §19.5): registration, staging, validation, canonical insert."""

from __future__ import annotations

import csv
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from mulenetx.audit.service import AuditService
from mulenetx.auth.service import Principal
from mulenetx.core import error_codes as ec
from mulenetx.core.config import Settings
from mulenetx.core.errors import AppError
from mulenetx.core.pagination import PageRequest
from mulenetx.core.timeutil import isoformat_utc, parse_utc, utcnow
from mulenetx.db.models.datasets import Dataset
from mulenetx.db.models.pipeline import IngestionRun, PipelineRun
from mulenetx.ingestion import staging
from mulenetx.ingestion.adapters import paysim_v1
from mulenetx.ingestion.validation import RejectionSummary, RowRejectedError
from mulenetx.jobs.pipeline_handler import enqueue_stage
from mulenetx.jobs.service import JobService
from mulenetx.jobs.stages.base import StageContext, StageOutcome

PIPELINE_VERSION = "ingest-paysim-v1"
SUPPORTED_ADAPTERS = {paysim_v1.ADAPTER}
BATCH = 10_000  # [PLAN DEFAULT §3.7]
_KEY_CHARS = re.compile(r"[^a-z0-9_-]")


def _sanitize(value: str) -> str:
    return _KEY_CHARS.sub("-", value.lower())


def base_dataset_key(name: str, dataset_version: str) -> str:
    """[PLAN DEFAULT §3.1] name (≤16) + '-v' + version, sanitized, ≤ 24 characters."""
    return (_sanitize(name)[:16] + "-v" + _sanitize(dataset_version))[:24]


@dataclass(frozen=True)
class Registration:
    dataset: Dataset
    ingestion_run: IngestionRun
    pipeline_run: PipelineRun


def ingestion_view(run: IngestionRun, dataset: Dataset | None, pipeline_run_id: uuid.UUID | None) -> dict[str, Any]:
    return {
        "ingestion_run_id": str(run.ingestion_run_id),
        "dataset_id": str(run.dataset_id),
        "dataset_key": None if dataset is None else dataset.dataset_key,
        "dataset_name": None if dataset is None else dataset.name,
        "dataset_version": None if dataset is None else dataset.dataset_version,
        "pipeline_run_id": None if pipeline_run_id is None else str(pipeline_run_id),
        "pipeline_version": run.pipeline_version,
        "status": run.status,
        "started_at": isoformat_utc(run.started_at),
        "completed_at": None if run.completed_at is None else isoformat_utc(run.completed_at),
        "records_seen": run.records_seen,
        "records_accepted": run.records_accepted,
        "records_rejected": run.records_rejected,
        "records_duplicate": run.records_duplicate,
        "rejection_summary": run.rejection_summary,
        "error_summary": run.error_summary,
    }


class IngestionService:
    def __init__(self, settings: Settings, audit: AuditService, jobs: JobService) -> None:
        self.settings = settings
        self.audit = audit
        self.jobs = jobs

    # ── registration (API and CLI) ─────────────────────────────────────────

    def normalized_adapter_config(self, adapter: str, adapter_config: dict[str, Any]) -> dict[str, Any]:
        if adapter not in SUPPORTED_ADAPTERS:
            raise AppError(ec.VALIDATION_ERROR, "Unsupported dataset adapter.", {"field": "adapter"})
        cfg = dict(adapter_config)
        anchor = cfg.get("epoch_anchor", isoformat_utc(self.settings.paysim_epoch_anchor))
        try:
            cfg["epoch_anchor"] = isoformat_utc(parse_utc(str(anchor)))
        except ValueError as exc:
            raise AppError(ec.VALIDATION_ERROR, details={"field": "adapter_config.epoch_anchor"}) from exc
        cfg["timestamp_resolution_seconds"] = paysim_v1.TIMESTAMP_RESOLUTION_SECONDS
        cfg["synthetic_injection"] = False
        cfg.setdefault("slice_rule", None)
        return cfg

    def register(
        self,
        db: Session,
        actor: Principal | None,
        *,
        name: str,
        source: str,
        dataset_version: str,
        schema_version: str,
        adapter: str,
        adapter_config: dict[str, Any],
        staged_path: Path,
        checksum: str,
        request_id: str | None,
    ) -> Registration:
        for field, value, limit in (
            ("name", name, 200),
            ("source", source, 100),
            ("dataset_version", dataset_version, 100),
            ("schema_version", schema_version, 50),
        ):
            if not value.strip() or len(value) > limit:
                raise AppError(ec.VALIDATION_ERROR, details={"field": field})
        cfg = self.normalized_adapter_config(adapter, adapter_config)
        if db.execute(
            select(Dataset).where(Dataset.checksum == checksum, Dataset.dataset_version == dataset_version)
        ).first():
            raise AppError(ec.DATASET_ALREADY_REGISTERED)
        if db.execute(select(Dataset).where(Dataset.name == name, Dataset.dataset_version == dataset_version)).first():
            raise AppError(
                ec.CONFLICT,
                "A different file is already registered under this name and version.",
                {"field": "dataset_version"},
            )
        key = self._unique_key(db, base_dataset_key(name, dataset_version))
        now = utcnow()
        dataset = Dataset(
            dataset_id=uuid.uuid4(),
            dataset_key=key,
            name=name,
            source=source,
            dataset_version=dataset_version,
            schema_version=schema_version,
            adapter=adapter,
            adapter_config=cfg,
            checksum=checksum,
            timestamp_resolution_seconds=paysim_v1.TIMESTAMP_RESOLUTION_SECONDS,
            is_synthetic_injection=False,
            created_at=now,
        )
        db.add(dataset)
        db.flush()
        ingestion = IngestionRun(
            ingestion_run_id=uuid.uuid4(),
            dataset_id=dataset.dataset_id,
            pipeline_version=PIPELINE_VERSION,
            started_at=now,
            status="CREATED",
            records_seen=0,
            records_accepted=0,
            records_rejected=0,
            records_duplicate=0,
            rejection_summary={"counts": {}, "samples": {}},
        )
        db.add(ingestion)
        db.flush()
        run = self.jobs.create_run(db, dataset.dataset_id, ingestion.ingestion_run_id)
        enqueue_stage(
            db,
            run,
            "INGESTING",
            self.settings.job_max_attempts,
            {"ingestion_run_id": str(ingestion.ingestion_run_id), "staged_path": str(staged_path)},
            requested_by=None if actor is None else actor.user_id,
            request_id=request_id,
        )
        self.audit.record_in(
            db,
            "ingestion.submit",
            "dataset",
            "SUCCESS",
            user_id=None if actor is None else actor.user_id,
            resource_id=str(dataset.dataset_id),
            metadata={"dataset_key": key, "dataset_version": dataset_version, "checksum": checksum},
        )
        db.commit()
        return Registration(dataset, ingestion, run)

    @staticmethod
    def _unique_key(db: Session, base: str) -> str:
        key, n = base, 1
        while db.execute(select(Dataset.dataset_id).where(Dataset.dataset_key == key)).first():
            n += 1
            suffix = f"-{n}"
            key = base[: 24 - len(suffix)] + suffix
        return key

    @staticmethod
    def check_header(path: Path) -> list[str]:
        with path.open("r", encoding="utf-8", newline="") as f:
            first = f.readline()
        header = next(iter(csv.reader([first])), [])
        return paysim_v1.header_problems(header)

    # ── INGEST job ─────────────────────────────────────────────────────────

    def execute(self, ctx: StageContext, ingestion_run_id: uuid.UUID, staged_path: Path) -> StageOutcome:
        rt = ctx.runtime
        with rt.session_factory() as db:
            run = db.get(IngestionRun, ingestion_run_id, with_for_update=True)
            dataset = db.get(Dataset, ctx.dataset_id)
            if run is None or dataset is None:
                raise LookupError("ingestion run or dataset missing")
            if run.status == "SUCCEEDED":
                return StageOutcome(run_updates={"ingestion_run_id": ingestion_run_id})
            run.status = "RUNNING"
            run.error_summary = None
            db.commit()
            anchor = parse_utc(str(dataset.adapter_config["epoch_anchor"]))
            key = dataset.dataset_key

        table = staging.create_staging_table(rt.engine, ingestion_run_id)
        summary = RejectionSummary()
        seen = 0
        batch: list[paysim_v1.NormalizedRow] = []
        with staged_path.open("r", encoding="utf-8", newline="") as stream:
            for ordinal, raw in paysim_v1.read_rows(stream):
                seen += 1
                try:
                    batch.append(paysim_v1.normalize(raw, ordinal, anchor))
                except RowRejectedError as rej:
                    summary.add(rej.code, ordinal)
                if len(batch) >= BATCH:
                    staging.copy_rows(rt.engine, table, batch)
                    batch = []
                    ctx.check()
        if batch:
            staging.copy_rows(rt.engine, table, batch)
        accepted = seen - summary.total

        def finalize(db: Session) -> None:
            self._canonical_insert(db, table, key, ctx.dataset_id, ingestion_run_id)
            run = db.get(IngestionRun, ingestion_run_id, with_for_update=True)
            assert run is not None
            run.status = "SUCCEEDED"
            run.completed_at = utcnow()
            run.records_seen = seen
            run.records_accepted = accepted
            run.records_rejected = summary.total
            run.records_duplicate = 0
            run.rejection_summary = summary.as_json()
            dataset_row = db.get(Dataset, ctx.dataset_id)
            assert dataset_row is not None
            dataset_row.record_count = accepted
            db.execute(text(f"DROP TABLE IF EXISTS {table}"))

        return StageOutcome(run_updates={"ingestion_run_id": ingestion_run_id}, finalize=finalize)

    @staticmethod
    def _canonical_insert(
        db: Session, table: str, key: str, dataset_id: uuid.UUID, ingestion_run_id: uuid.UUID
    ) -> None:
        """Accounts ON CONFLICT DO NOTHING, then accepted transactions (one transaction, §7.2, §6.6)."""
        db.execute(
            text(
                f"""
                INSERT INTO accounts (account_id, dataset_id, source_account_ref, account_type)
                SELECT :key || ':' || ref, :dataset_id, ref, min(account_type)
                FROM (SELECT source_account_ref AS ref, source_account_type AS account_type FROM {table}
                      UNION ALL
                      SELECT destination_account_ref, destination_account_type FROM {table}) a
                GROUP BY ref
                ORDER BY ref
                ON CONFLICT DO NOTHING
                """  # noqa: S608 - table name derives from the run UUID, never from input
            ),
            {"key": key, "dataset_id": dataset_id},
        )
        db.execute(
            text(
                f"""
                INSERT INTO transactions (transaction_id, dataset_id, ingestion_run_id, source_transaction_ref,
                    source_account_id, destination_account_id, amount, "timestamp", transaction_type, fraud_label,
                    source_record_hash)
                SELECT :key || ':' || source_transaction_ref, :dataset_id, :run_id, source_transaction_ref,
                       :key || ':' || source_account_ref, :key || ':' || destination_account_ref, amount, ts,
                       transaction_type, fraud_label, source_record_hash
                FROM {table}
                ORDER BY ordinal
                """  # noqa: S608 - table name derives from the run UUID, never from input
            ),
            {"key": key, "dataset_id": dataset_id, "run_id": ingestion_run_id},
        )

    def on_failure(self, runtime_factory: Any, ingestion_run_id: uuid.UUID, message: str) -> None:
        with runtime_factory() as db:
            run = db.get(IngestionRun, ingestion_run_id, with_for_update=True)
            if run is not None and run.status != "SUCCEEDED":
                run.status = "FAILED"
                run.error_summary = message[:2000]
                db.commit()

    # ── reads ──────────────────────────────────────────────────────────────

    @staticmethod
    def get(db: Session, ingestion_run_id: uuid.UUID) -> dict[str, Any]:
        run = db.get(IngestionRun, ingestion_run_id)
        if run is None:
            raise AppError(ec.NOT_FOUND, details={"resource": "ingestion"})
        return ingestion_view(run, db.get(Dataset, run.dataset_id), _pipeline_run_for(db, ingestion_run_id))

    @staticmethod
    def list(
        db: Session, page: PageRequest, dataset_id: uuid.UUID | None, status: str | None
    ) -> tuple[list[dict[str, Any]], int]:
        q = select(IngestionRun)
        if dataset_id is not None:
            q = q.where(IngestionRun.dataset_id == dataset_id)
        if status is not None:
            q = q.where(IngestionRun.status == status)
        total = int(db.execute(select(func.count()).select_from(q.subquery())).scalar_one())
        runs = db.execute(
            q.order_by(IngestionRun.started_at.desc(), IngestionRun.ingestion_run_id)
            .offset(page.offset)
            .limit(page.page_size)
        ).scalars()
        items = [
            ingestion_view(r, db.get(Dataset, r.dataset_id), _pipeline_run_for(db, r.ingestion_run_id)) for r in runs
        ]
        return items, total


def _pipeline_run_for(db: Session, ingestion_run_id: uuid.UUID) -> uuid.UUID | None:
    return db.execute(
        select(PipelineRun.pipeline_run_id)
        .where(PipelineRun.ingestion_run_id == ingestion_run_id)
        .order_by(PipelineRun.started_at)
        .limit(1)
    ).scalar_one_or_none()


def parse_adapter_config(raw: str | None) -> dict[str, Any]:
    if raw is None or not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppError(ec.VALIDATION_ERROR, details={"field": "adapter_config"}) from exc
    if not isinstance(value, dict):
        raise AppError(ec.VALIDATION_ERROR, details={"field": "adapter_config"})
    return value
