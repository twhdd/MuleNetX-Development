"""Command-line entry points (`mulenetx <command>`)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from mulenetx.core.config import get_settings
from mulenetx.core.logging import configure_logging


def cmd_migrate_neo4j(args: argparse.Namespace) -> int:
    from mulenetx.graph.neo4j_client import Neo4jClient

    s = get_settings()
    client = Neo4jClient(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
    try:
        client.create_schema()
    finally:
        client.close()
    print("neo4j constraints and indexes are in place")
    return 0


def cmd_check_schema(args: argparse.Namespace) -> int:
    from mulenetx.db.engine import make_engine
    from mulenetx.db.schema_version import code_head, database_revision

    engine = make_engine(get_settings().postgres_dsn, pool_size=1)
    try:
        revision = database_revision(engine)
    finally:
        engine.dispose()
    if revision != code_head():
        print(f"schema version mismatch: database={revision} code={code_head()}", file=sys.stderr)
        return 1
    print(f"schema version {revision} matches")
    return 0


def cmd_bootstrap_admin(args: argparse.Namespace) -> int:
    from mulenetx.audit.service import AuditService
    from mulenetx.auth.passwords import Passwords
    from mulenetx.auth.service import AuthService
    from mulenetx.core.errors import AppError
    from mulenetx.core.runtime import Runtime

    s = get_settings()
    username = s.mulenetx_bootstrap_admin_username
    password = s.mulenetx_bootstrap_admin_password
    if not username or not password:
        print("MULENETX_BOOTSTRAP_ADMIN_USERNAME and MULENETX_BOOTSTRAP_ADMIN_PASSWORD are required", file=sys.stderr)
        return 2
    rt = Runtime(s)
    service = AuthService(s, AuditService(rt.session_factory), Passwords(s))
    try:
        with rt.session_factory() as db:
            user = service.bootstrap_admin(db, username, password)
    except AppError as exc:
        print(exc.message, file=sys.stderr)
        return 1
    finally:
        rt.close()
    print(f"administrator {user.username} created")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Register a server-side file under the same contract as POST /api/v1/ingestion (SRS §19.2 note)."""
    import json
    import shutil
    from pathlib import Path

    from mulenetx.audit.service import AuditService
    from mulenetx.core.errors import AppError
    from mulenetx.core.runtime import Runtime
    from mulenetx.ingestion import staging
    from mulenetx.ingestion.service import IngestionService
    from mulenetx.jobs.service import JobService

    s = get_settings()
    source = Path(args.path).resolve()
    if not source.is_file():
        print(f"no such file: {source}", file=sys.stderr)
        return 2
    staging_dir = Path(s.staging_dir).resolve()
    if staging_dir not in source.parents:
        staging_dir.mkdir(parents=True, exist_ok=True)
        target = staging_dir / f"cli-{source.name}"
        shutil.copyfile(source, target)
        source = target
    checksum, size = staging.file_checksum(source)
    if size > s.max_upload_bytes and not args.allow_large:
        print("file exceeds max_upload_bytes; pass --allow-large for server-side registration", file=sys.stderr)
    rt = Runtime(s)
    audit = AuditService(rt.session_factory)
    service = IngestionService(s, audit, JobService(s, audit))
    try:
        missing = service.check_header(source)
        if missing:
            print(f"missing required columns: {', '.join(missing)}", file=sys.stderr)
            return 1
        with rt.session_factory() as db:
            reg = service.register(
                db,
                None,
                name=args.name,
                source=args.source,
                dataset_version=args.dataset_version,
                schema_version=args.schema_version,
                adapter=args.adapter,
                adapter_config=json.loads(args.adapter_config) if args.adapter_config else {},
                staged_path=source,
                checksum=checksum,
                request_id=None,
            )
    except AppError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 1
    finally:
        rt.close()
    print(
        json.dumps(
            {
                "dataset_id": str(reg.dataset.dataset_id),
                "dataset_key": reg.dataset.dataset_key,
                "ingestion_run_id": str(reg.ingestion_run.ingestion_run_id),
                "pipeline_run_id": str(reg.pipeline_run.pipeline_run_id),
            }
        )
    )
    return 0


def cmd_export_openapi(args: argparse.Namespace) -> int:
    from mulenetx.openapi import write_openapi

    path = write_openapi(args.out)
    print(f"wrote {path}")
    return 0


def cmd_export_errors(args: argparse.Namespace) -> int:
    from pathlib import Path

    from mulenetx.core.error_codes import catalogue_markdown

    path = Path(args.out)
    path.write_text(catalogue_markdown())
    print(f"wrote {path}")
    return 0


COMMANDS: dict[str, tuple[Callable[[argparse.Namespace], int], str]] = {
    "ingest": (cmd_ingest, "register a server-side CSV (same contract as POST /api/v1/ingestion)"),
    "bootstrap-admin": (cmd_bootstrap_admin, "create the first ADMIN from the environment (refuses if one exists)"),
    "migrate-neo4j": (cmd_migrate_neo4j, "create the Neo4j constraints and indexes (SRS §6.8.1)"),
    "check-schema": (cmd_check_schema, "exit 1 unless the database schema version equals the code head"),
    "export-openapi": (cmd_export_openapi, "write the OpenAPI document (default docs/openapi.json)"),
    "export-errors": (cmd_export_errors, "write the error catalogue (default docs/api-errors.md)"),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mulenetx")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, (_fn, help_text) in COMMANDS.items():
        p = sub.add_parser(name, help=help_text)
        if name == "ingest":
            p.add_argument("--path", required=True)
            p.add_argument("--name", required=True)
            p.add_argument("--dataset-version", required=True)
            p.add_argument("--source", default="paysim")
            p.add_argument("--schema-version", default="paysim-1")
            p.add_argument("--adapter", default="paysim-v1")
            p.add_argument("--adapter-config", default=None)
            p.add_argument("--allow-large", action="store_true")
        if name == "export-openapi":
            p.add_argument("--out", default="../docs/openapi.json")
        if name == "export-errors":
            p.add_argument("--out", default="../docs/api-errors.md")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command not in ("export-openapi", "export-errors"):  # the exports need no environment
        configure_logging(get_settings().log_level)
    fn, _ = COMMANDS[args.command]
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())
