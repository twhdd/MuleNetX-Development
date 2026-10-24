"""AT-OPS-06: on a clean database, every PK, FK, UNIQUE and CHECK of SRS §6.3 rejects a violating row;
composite community FKs are enforced; "Imm." columns cannot be updated; the app role cannot UPDATE or
DELETE append-only tables (SRS §6.5)."""

from __future__ import annotations

import re
import sys
import uuid
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from psycopg import errors

from tests import dbutil
from tests.factories import FACTORIES, TS, Fresh, insert

sys.path.insert(0, str(dbutil.BACKEND.parent / "scripts"))
import schema_check  # noqa: E402

pytestmark = pytest.mark.integration

DB = "mulenetx_ops06"
APPEND_ONLY = (
    "findings",
    "audit_events",
    "transactions",
    "risk_assessments",
    "account_feature_values",
    "shap_explanations",
    "propagation_contributions",
    "ring_feature_sets",
    "ring_risk_assessments",
    "temporal_motifs",
    "intervention_candidates",
    "evaluation_metrics",
)
# Constraint cells whose rule is not a single-row CHECK: enforced elsewhere and tested elsewhere.
CHECK_ENFORCED_ELSEWHERE = {
    ("ingestion_runs", "rejection_summary"),  # content rule (≤ 100 samples) enforced by the ingestion service
    ("account_feature_values", "graph_snapshot_id"),  # cross-table data_cutoff ≤ as_of: BEFORE INSERT trigger
}
MULTI_COLUMN_CHECKS: dict[str, dict[str, Any]] = {
    "afv_lengths_ck": {"feature_values": [1.0], "feature_states": [0, 1]},
    "rfs_times_ck": {"transaction_count": 0, "start_time": TS, "end_time": TS},
    "cases_closed_at_ck": {"status": "CLOSED"},
    # single-column check that needs a companion value so that rfs_times_ck (evaluated first) passes
    "rfs_transaction_count_ck": {"transaction_count": -1, "start_time": TS, "end_time": TS},
}


@pytest.fixture(scope="module")
def conn() -> Iterator[psycopg.Connection[Any]]:
    dbutil.create_fresh_database(DB)
    dbutil.upgrade(dbutil.owner_dsn(DB))
    with psycopg.connect(dbutil.owner_dsn(DB, driver=False)) as c:
        yield c


@pytest.fixture(scope="module")
def constraints(conn: psycopg.Connection[Any]) -> list[tuple[str, str, str, list[str], list[str]]]:
    rows = conn.execute(
        """
        SELECT c.conrelid::regclass::text, c.conname, c.contype,
               ARRAY(SELECT a.attname FROM unnest(c.conkey) k JOIN pg_attribute a
                     ON a.attrelid = c.conrelid AND a.attnum = k ORDER BY a.attname)::text[],
               ARRAY(SELECT a.attname FROM unnest(c.conkey) WITH ORDINALITY k(n, i) JOIN pg_attribute a
                     ON a.attrelid = c.conrelid AND a.attnum = k.n ORDER BY k.i)::text[]
        FROM pg_constraint c
        WHERE c.connamespace = 'public'::regnamespace AND c.contype IN ('p','u','f','c')
        ORDER BY 1, 2
        """
    ).fetchall()
    return [(r[0], r[1], r[2], list(r[3]), list(r[4])) for r in rows if r[0] in FACTORIES]


def _col_types(conn: psycopg.Connection[Any], table: str) -> dict[str, str]:
    rows = conn.execute(
        "SELECT column_name, udt_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s",
        (table,),
    ).fetchall()
    return {r[0]: r[1] for r in rows}


def _expect(conn: psycopg.Connection[Any], table: str, row: dict[str, Any]) -> psycopg.Error | None:
    """Insert inside a savepoint that is always rolled back; return the error, if any."""
    try:
        with conn.transaction(force_rollback=True):
            insert(conn, table, row)
    except psycopg.Error as exc:
        return exc
    return None


def _missing(udt: str, n: int) -> Any:
    return uuid.uuid4() if udt == "uuid" else f"missing:{n}"


def test_AT_OPS_06_all_36_tables_have_factories() -> None:
    assert sorted(FACTORIES) == sorted(schema_check.parse_srs())


def test_AT_OPS_06_primary_and_unique_constraints_reject_duplicates(
    conn: psycopg.Connection[Any], constraints: Any
) -> None:
    f = Fresh(conn)
    checked = 0
    keys = {(t, n): c for t, n, k, c, _ in constraints if k in ("p", "u")}
    for table, name, kind, cols, _ in constraints:
        if kind not in ("p", "u"):
            continue
        if table == "active_context":
            dup = {"singleton": True, "updated_at": TS}
        else:
            with conn.transaction():
                first = f.make(table)
            dup = f.build(table)
            dup.update({c: first[c] for c in cols})
        err = _expect(conn, table, dup)
        assert isinstance(err, errors.UniqueViolation), f"{name}: expected unique violation, got {err!r}"
        if err.diag.constraint_name != name:
            # A superset key (for example UNIQUE(dataset_id, account_id) backing a composite FK) is implied
            # by a stronger key on a subset of its columns; that stronger key must be what fired.
            stronger = keys[(table, err.diag.constraint_name)]
            assert set(stronger) < set(cols), f"{name}: reported {err.diag.constraint_name}"
        checked += 1
    assert checked >= 40


def test_AT_OPS_06_foreign_keys_reject_missing_parents(conn: psycopg.Connection[Any], constraints: Any) -> None:
    f = Fresh(conn)
    fks: dict[str, list[tuple[str, list[str]]]] = {}
    for table, name, kind, cols, _ in constraints:
        if kind == "f":
            fks.setdefault(table, []).append((name, cols))
    checked = 0
    for table, items in fks.items():
        types = _col_types(conn, table)
        for name, cols in items:
            others = {c for n, cs in items if n != name for c in cs}
            target = [c for c in cols if c not in others] or cols
            with conn.transaction():
                row = f.build(table) if table != "active_context" else {"singleton": True, "updated_at": TS}
            if table == "active_context":
                conn.execute("DELETE FROM active_context")
            row.update({c: _missing(types[c], f.n()) for c in target})
            err = _expect(conn, table, row)
            if table == "active_context":
                conn.execute("INSERT INTO active_context (singleton, updated_at) VALUES (TRUE, now())")
            assert isinstance(err, errors.ForeignKeyViolation), f"{name}: expected FK violation, got {err!r}"
            candidates = {n for n, cs in items if set(cs) & set(target)}
            assert err.diag.constraint_name in candidates, f"{name}: reported {err.diag.constraint_name}"
            checked += 1
    assert checked >= 100


CANDIDATES_BY_TYPE: dict[str, list[Any]] = {
    "numeric": [-1, 2, 0.4, 0.6, 1.5, 0],
    "int2": [-1, 0, 4, 5],
    "int4": [-1, 0],
    "int8": [-1],
    "float8": [-1.0],
    "varchar": ["", "BOGUS_VALUE"],
    "bpchar": [""],
    "text": ["", "x" * 20001],
    "bool": [False],
    "_int2": [[5, 5]],
}


def test_AT_OPS_06_check_constraints_reject_invalid_values(conn: psycopg.Connection[Any], constraints: Any) -> None:
    f = Fresh(conn)
    checked = 0
    for table, name, kind, cols, _ in constraints:
        if kind != "c":
            continue
        if table == "active_context":
            conn.execute("DELETE FROM active_context")
            err = _expect(conn, table, {"singleton": False, "updated_at": TS})
            conn.execute("INSERT INTO active_context (singleton, updated_at) VALUES (TRUE, now())")
            assert isinstance(err, errors.CheckViolation) and err.diag.constraint_name == name
            checked += 1
            continue
        if name in MULTI_COLUMN_CHECKS:
            options: list[dict[str, Any]] = [MULTI_COLUMN_CHECKS[name]]
        else:
            assert len(cols) == 1, f"{name}: multi-column check needs an explicit case"
            udt = _col_types(conn, table)[cols[0]]
            options = [{cols[0]: v} for v in CANDIDATES_BY_TYPE[udt]]
        hit = False
        for override in options:
            with conn.transaction():
                row = f.build(table)
            row.update(override)
            err = _expect(conn, table, row)
            if isinstance(err, errors.CheckViolation) and err.diag.constraint_name == name:
                hit = True
                break
        assert hit, f"{name} on {table}: no candidate value was rejected"
        checked += 1
    assert checked >= 100


def test_AT_OPS_06_srs_declared_constraints_exist(constraints: Any) -> None:
    """Every column whose SRS §6.3 constraint cell names an FK, UNIQUE, PK or CHECK is covered, and every
    table-level PK/UNIQUE written in the SRS prose exists with exactly those columns."""
    by_table: dict[str, dict[str, list[set[str]]]] = {}
    for table, _name, kind, cols, _ in constraints:
        by_table.setdefault(table, {"p": [], "u": [], "f": [], "c": []})[kind].append(set(cols))
    spec = schema_check.parse_srs()
    text = schema_check.SRS.read_text(encoding="utf-8")
    problems: list[str] = []
    cells = _constraint_cells(text)
    for table, cols in spec.items():
        kinds = by_table.get(table, {"p": [], "u": [], "f": [], "c": []})
        if not kinds["p"]:
            problems.append(f"{table}: no PK")
        for col in cols:
            cell = cells[(table, col.name)]
            if re.search(r"\bFK\b", cell) and not any(col.name in s for s in kinds["f"]):
                problems.append(f"{table}.{col.name}: SRS FK missing")
            if re.search(r"\b(UNIQUE|PK)\b", cell) and not any(col.name in s for s in kinds["u"] + kinds["p"]):
                problems.append(f"{table}.{col.name}: SRS UNIQUE/PK missing")
            wants_check = re.search(r"CHECK|non-empty|≥|≤|> 0|\[a-z0-9", cell)
            if (
                wants_check
                and (table, col.name) not in CHECK_ENFORCED_ELSEWHERE
                and not any(col.name in s for s in kinds["c"])
            ):
                problems.append(f"{table}.{col.name}: SRS CHECK missing")
    for table, keyword, columns in _prose_keys(text):
        want = {c.strip() for c in columns.split(",")}
        pool = by_table[table]["p"] if keyword == "PK" else by_table[table]["u"] + by_table[table]["p"]
        if want not in pool:
            problems.append(f"{table}: {keyword} {sorted(want)} missing")
    assert problems == []


def _constraint_cells(text: str) -> dict[tuple[str, str], str]:
    section = text[text.index("## 6.3 PostgreSQL Physical Schema") : text.index("## 6.4 ")]
    out: dict[tuple[str, str], str] = {}
    table = None
    for line in section.splitlines():
        m = re.match(r"^#### `([a-z_]+)`", line)
        if m:
            table = m.group(1)
            continue
        if table and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 5 and cells[0] not in ("Column",) and not set(cells[0]) <= {"-"}:
                out[(table, cells[0])] = cells[3]
    return out


def _prose_keys(text: str) -> list[tuple[str, str, str]]:
    section = text[text.index("## 6.3 PostgreSQL Physical Schema") : text.index("## 6.4 ")]
    found: list[tuple[str, str, str]] = []
    table = None
    for line in section.splitlines():
        m = re.match(r"^#### `([a-z_]+)`", line)
        if m:
            table = m.group(1)
            continue
        if table is None or line.startswith("|"):
            continue
        for km in re.finditer(r"\b(PK|UNIQUE):? `\(([^)]*)\)`", line):
            found.append((table, km.group(1), km.group(2)))
    return found


def _changed_expr(udt: str, col: str) -> str:
    c = f'"{col}"'
    return {
        "uuid": "gen_random_uuid()",
        "varchar": f"CASE WHEN {c} = 'ALT' THEN 'ALT2' ELSE 'ALT' END",
        "text": f"COALESCE({c}, '') || 'x'",
        "bpchar": f"CASE WHEN {c} = repeat('e', 64) THEN repeat('f', 64) ELSE repeat('e', 64) END",
        "int2": f"COALESCE({c}, 0) + 1",
        "int4": f"COALESCE({c}, 0) + 1",
        "int8": f"COALESCE({c}, 0) + 1",
        "numeric": f"CASE WHEN {c} = 0.25 THEN 0.75 ELSE 0.25 END",
        "float8": f"COALESCE({c}, 0) + 1",
        "bool": f"NOT COALESCE({c}, FALSE)",
        "timestamptz": f"COALESCE({c}, now()) + interval '1 second'",
        "jsonb": "'{\"changed\": true}'::jsonb",
        "_float8": f"array_append({c}, 9.0)",
        "_int2": f"array_append({c}, 1::smallint)",
    }[udt]


def test_AT_OPS_06_immutable_columns_reject_updates(conn: psycopg.Connection[Any]) -> None:
    f = Fresh(conn)
    spec = schema_check.parse_srs()
    checked = 0
    for table, cols in sorted(spec.items()):
        types = _col_types(conn, table)
        with conn.transaction():
            if table != "active_context":
                f.make(table)
        for col in cols:
            if col.mutable != "Imm.":
                continue
            sql = f'UPDATE "{table}" SET "{col.name}" = {_changed_expr(types[col.name], col.name)}'
            try:
                with conn.transaction(force_rollback=True):
                    conn.execute(sql)
                raise AssertionError(f"{table}.{col.name}: update was accepted")
            except errors.IntegrityConstraintViolation as exc:
                assert "is immutable" in str(exc), f"{table}.{col.name}: {exc}"
            checked += 1
    assert checked > 300


def test_AT_OPS_06_once_columns_change_only_from_null(conn: psycopg.Connection[Any]) -> None:
    f = Fresh(conn)
    with conn.transaction():
        g = f.make("graph_snapshots", status="VALIDATING")
    with conn.transaction():
        conn.execute(
            "UPDATE graph_snapshots SET ready_at = now(), status = 'READY' WHERE graph_snapshot_id = %s",
            (g["graph_snapshot_id"],),
        )
    with pytest.raises(errors.IntegrityConstraintViolation), conn.transaction():
        conn.execute(
            "UPDATE graph_snapshots SET ready_at = now() + interval '1 hour' WHERE graph_snapshot_id = %s",
            (g["graph_snapshot_id"],),
        )
    with conn.transaction():
        u = f.make("users")
        conn.execute("UPDATE users SET role = 'ADMIN', is_active = FALSE WHERE user_id = %s", (u["user_id"],))


def test_AT_OPS_06_app_role_cannot_update_or_delete_append_only(conn: psycopg.Connection[Any]) -> None:
    f = Fresh(conn)
    with conn.transaction():
        for table in APPEND_ONLY:
            f.make(table)
    conn.commit()
    with psycopg.connect(dbutil.app_dsn(DB, driver=False)) as app:
        for table in APPEND_ONLY:
            first_col = _col_types(conn, table)
            col = sorted(first_col)[0]
            for sql in (f'UPDATE "{table}" SET "{col}" = "{col}"', f'DELETE FROM "{table}"'):
                with pytest.raises(errors.InsufficientPrivilege), app.transaction():
                    app.execute(sql)
            app.execute(f'SELECT count(*) FROM "{table}"').fetchone()


def test_AT_OPS_06_purge_function_guards_succeeded_runs(conn: psycopg.Connection[Any]) -> None:
    f = Fresh(conn)
    with conn.transaction():
        ra = f.make("risk_assessments")
    conn.commit()
    with psycopg.connect(dbutil.app_dsn(DB, driver=False)) as app:
        app.execute("SELECT purge_scoring_outputs(%s)", (ra["scoring_run_id"],))
        app.commit()
        n = app.execute("SELECT count(*) FROM risk_assessments WHERE scoring_run_id = %s", (ra["scoring_run_id"],))
        assert n.fetchone() == (0,)
    with conn.transaction():
        ra2 = f.make("risk_assessments")
        conn.execute("UPDATE scoring_runs SET status='SUCCEEDED' WHERE scoring_run_id = %s", (ra2["scoring_run_id"],))
    conn.commit()
    with psycopg.connect(dbutil.app_dsn(DB, driver=False)) as app, pytest.raises(errors.RaiseException):
        app.execute("SELECT purge_scoring_outputs(%s)", (ra2["scoring_run_id"],))


def test_AT_OPS_06_feature_snapshot_after_cutoff_rejected_by_database(conn: psycopg.Connection[Any]) -> None:
    f = Fresh(conn)
    with conn.transaction():
        row = f.build("account_feature_values")
    row["as_of"] = TS.replace(hour=1)  # snapshot data_cutoff is TS (10:00) > as_of
    err = _expect(conn, "account_feature_values", row)
    assert isinstance(err, errors.CheckViolation)
