"""Migrations upgrade, downgrade and upgrade again on an empty database (T03)."""

import sys

import psycopg
import pytest

from tests import dbutil

pytestmark = pytest.mark.integration

sys.path.insert(0, str(dbutil.BACKEND.parent / "scripts"))
import schema_check  # noqa: E402

DB = "mulenetx_migtest"
GROUP_1_2 = [
    "users",
    "auth_sessions",
    "datasets",
    "accounts",
    "transactions",
    "audit_events",
    "dataset_profiles",
    "ingestion_runs",
    "pipeline_runs",
    "jobs",
    "graph_snapshots",
    "analytics_runs",
    "feature_versions",
    "model_versions",
    "risk_logic_versions",
    "scoring_runs",
    "active_context",
]


def _tables() -> set[str]:
    with psycopg.connect(dbutil.owner_dsn(DB, driver=False)) as conn:
        rows = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall()
    return {r[0] for r in rows} - {"alembic_version"}


def test_upgrade_downgrade_upgrade() -> None:
    dbutil.create_fresh_database(DB)
    dsn = dbutil.owner_dsn(DB)
    dbutil.upgrade(dsn)
    first = _tables()
    assert set(GROUP_1_2) <= first
    dbutil.downgrade(dsn)
    assert _tables() == set()
    dbutil.upgrade(dsn)
    assert _tables() == first


def test_schema_matches_srs_for_group_1_2() -> None:
    dbutil.create_fresh_database(DB)
    dbutil.upgrade(dbutil.owner_dsn(DB))
    assert schema_check.check(dbutil.owner_dsn(DB), GROUP_1_2) == []


def test_active_context_singleton_inserted() -> None:
    dbutil.create_fresh_database(DB)
    dbutil.upgrade(dbutil.owner_dsn(DB))
    with psycopg.connect(dbutil.owner_dsn(DB, driver=False)) as conn:
        assert conn.execute("SELECT count(*), bool_and(singleton) FROM active_context").fetchone() == (1, True)


def test_schema_matches_srs_for_all_36_tables() -> None:
    dbutil.create_fresh_database(DB)
    dbutil.upgrade(dbutil.owner_dsn(DB))
    assert len(schema_check.parse_srs()) == 36
    assert schema_check.check(dbutil.owner_dsn(DB)) == []
