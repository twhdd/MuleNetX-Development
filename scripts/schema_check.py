"""Compare the live PostgreSQL schema with the column tables of SRS §6.3.

Usage: `python scripts/schema_check.py [--dsn DSN] [--tables t1,t2]`
Exit code 0 when no difference is found for the selected tables (all §6.3 tables by default).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
SRS = ROOT / "docs" / "SRS.md"


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    nullable: bool
    mutable: str


def parse_srs(path: Path = SRS) -> dict[str, list[Column]]:
    text = path.read_text(encoding="utf-8")
    start = text.index("## 6.3 PostgreSQL Physical Schema")
    end = text.index("## 6.4 ")
    section = text[start:end]
    tables: dict[str, list[Column]] = {}
    current: str | None = None
    for line in section.splitlines():
        heading = re.match(r"^#### `([a-z_]+)`", line)
        if heading:
            current = heading.group(1)
            tables[current] = []
            continue
        if current is None or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5 or cells[0] in ("Column", "---") or set(cells[0]) <= {"-"}:
            continue
        tables[current].append(Column(cells[0], normalize_srs_type(cells[1]), cells[2] == "Yes", cells[4]))
    return tables


def normalize_srs_type(t: str) -> str:
    t = t.strip().upper()
    m = re.fullmatch(r"VARCHAR\((\d+)\)", t)
    if m:
        return f"varchar({m.group(1)})"
    m = re.fullmatch(r"CHAR\((\d+)\)", t)
    if m:
        return f"char({m.group(1)})"
    m = re.fullmatch(r"NUMERIC\((\d+),\s*(\d+)\)", t)
    if m:
        return f"numeric({m.group(1)},{m.group(2)})"
    simple = {
        "UUID": "uuid",
        "TEXT": "text",
        "BOOLEAN": "bool",
        "TIMESTAMPTZ": "timestamptz",
        "INTEGER": "int4",
        "BIGINT": "int8",
        "SMALLINT": "int2",
        "JSONB": "jsonb",
        "DOUBLE PRECISION": "float8",
        "DOUBLE PRECISION[]": "float8[]",
        "SMALLINT[]": "int2[]",
    }
    if t not in simple:
        raise ValueError(f"unknown SRS type {t!r}")
    return simple[t]


def db_columns(conn: psycopg.Connection[tuple[object, ...]], table: str) -> dict[str, tuple[str, bool]]:
    rows = conn.execute(
        """
        SELECT column_name, data_type, udt_name, character_maximum_length, numeric_precision,
               numeric_scale, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()
    out: dict[str, tuple[str, bool]] = {}
    for name, data_type, udt, char_len, num_p, num_s, nullable in rows:
        if data_type == "character varying":
            t = f"varchar({char_len})"
        elif data_type == "character":
            t = f"char({char_len})"
        elif data_type == "numeric":
            t = f"numeric({num_p},{num_s})"
        elif data_type == "ARRAY":
            t = f"{str(udt).lstrip('_')}[]"
        else:
            t = str(udt)
        out[str(name)] = (t, nullable == "YES")
    return out


def check(dsn: str, tables: list[str] | None = None) -> list[str]:
    spec = parse_srs()
    selected = tables if tables else sorted(spec)
    problems: list[str] = []
    conn_dsn = dsn.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(conn_dsn) as conn:
        for table in selected:
            if table not in spec:
                problems.append(f"{table}: not in SRS §6.3")
                continue
            actual = db_columns(conn, table)
            if not actual:
                problems.append(f"{table}: table missing")
                continue
            expected = {c.name: c for c in spec[table]}
            for name in expected.keys() - actual.keys():
                problems.append(f"{table}.{name}: column missing")
            for name in actual.keys() - expected.keys():
                problems.append(f"{table}.{name}: column not in SRS")
            for name in sorted(expected.keys() & actual.keys()):
                exp = expected[name]
                a_type, a_null = actual[name]
                if exp.type != a_type:
                    problems.append(f"{table}.{name}: type {a_type} != SRS {exp.type}")
                if exp.nullable != a_null:
                    problems.append(f"{table}.{name}: nullable {a_null} != SRS {exp.nullable}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=os.environ.get("POSTGRES_OWNER_DSN") or os.environ.get("POSTGRES_DSN"))
    parser.add_argument("--tables", default="")
    args = parser.parse_args()
    if not args.dsn:
        print("a DSN is required (--dsn or POSTGRES_OWNER_DSN)", file=sys.stderr)
        return 2
    tables = [t for t in args.tables.split(",") if t] or None
    problems = check(args.dsn, tables)
    for p in problems:
        print(p)
    n = len(tables) if tables else len(parse_srs())
    print(f"schema_check: {n} tables checked, {len(problems)} differences")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
