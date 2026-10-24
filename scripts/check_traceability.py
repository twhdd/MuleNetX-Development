"""Requirement → acceptance test → test → last result (PLAN T45, SRS §28.2, §30.1).

Parses the §30.1 traceability table and the §28 acceptance matrices from docs/SRS.md, finds every test whose
name carries each AT-ID (`test_AT_SEC_04...`), reads the latest outcome of each test from the JUnit XML files
in backend/reports/ (written by the make test targets), and writes docs/traceability.md.

Exit status 0 only when every requirement links at least one AT-ID, every AT-ID has at least one test, and
every one of those tests passed in its latest recorded run. Anything else is listed as a gap.

    make traceability
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET  # noqa: S405 - reads our own pytest reports
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRS = ROOT / "docs" / "SRS.md"
TESTS = ROOT / "backend" / "tests"
REPORTS = ROOT / "backend" / "reports"
OUT = ROOT / "docs" / "traceability.md"

AT = re.compile(r"AT-[A-Z0-9]+-\d+(?:\.\.\d+)?")
TEST_DEF = re.compile(r"^\s*def (test_\w+)\(", re.M)


@dataclass
class Test:
    file: str
    name: str
    outcomes: dict[str, str] = field(default_factory=dict)  # junit case name (with params) -> outcome

    @property
    def result(self) -> str:
        if not self.outcomes:
            return "not run"
        values = set(self.outcomes.values())
        if values == {"passed"}:
            return "passed"
        for worst in ("failed", "error", "skipped"):
            if worst in values:
                return worst
        return "unknown"


def expand(token: str) -> list[str]:
    """AT-SEC-01..05 → AT-SEC-01 … AT-SEC-05."""
    if ".." not in token:
        return [token]
    head, last = token.split("..")
    prefix, first = head.rsplit("-", 1)
    return [f"{prefix}-{n:0{len(first)}d}" for n in range(int(first), int(last) + 1)]


def srs_section(lines: list[str], start: str, stop: str) -> list[str]:
    i = next(k for k, line in enumerate(lines) if line.startswith(start))
    j = next(k for k in range(i + 1, len(lines)) if lines[k].startswith(stop))
    return lines[i:j]


def parse_srs() -> tuple[dict[str, list[str]], list[str]]:
    lines = SRS.read_text().splitlines()
    requirements: dict[str, list[str]] = {}
    for line in srs_section(lines, "## 30.1", "## 30.2"):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        ident = cells[0].replace("†", "").strip()  # † marks requirements added in v1.3.3
        if len(cells) >= 8 and re.fullmatch(r"[A-Z]+(?:-[A-Z]+)?-\d+", ident):
            requirements[ident] = [a for token in AT.findall(cells[-1]) for a in expand(token)]
    acceptance = []
    for line in srs_section(lines, "# 28.", "# 29."):
        m = re.match(r"\| (AT-[A-Z0-9]+-\d+) \|", line)
        if m:
            acceptance.append(m.group(1))
    return requirements, acceptance


def discover() -> dict[str, list[Test]]:
    by_at: dict[str, list[Test]] = defaultdict(list)
    for path in sorted(TESTS.rglob("test_*.py")):
        for name in TEST_DEF.findall(path.read_text()):
            m = re.match(r"test_(AT_[A-Z0-9]+_\d+)(?:_|$)", name)
            if m:
                by_at[m.group(1).replace("_", "-")].append(Test(str(path.relative_to(ROOT)), name))
    return by_at


def load_results(by_at: dict[str, list[Test]]) -> list[str]:
    index = {(t.file, t.name): t for tests in by_at.values() for t in tests}
    files = sorted(REPORTS.glob("*.xml"), key=lambda p: p.stat().st_mtime) if REPORTS.exists() else []
    for report in files:  # later reports override earlier ones
        for case in ET.parse(report).getroot().iter("testcase"):  # noqa: S314 - our own report
            module = case.get("classname", "").replace(".", "/") + ".py"
            name = case.get("name", "")
            base = name.split("[", 1)[0]
            test = index.get((f"backend/{module}", base))
            if test is None:
                continue
            outcome = "passed"
            for child in case:
                if child.tag in ("failure", "error", "skipped"):
                    outcome = {"failure": "failed"}.get(child.tag, child.tag)
            test.outcomes[name] = outcome
    return [p.name for p in files]


def main() -> int:
    requirements, acceptance = parse_srs()
    by_at = discover()
    reports = load_results(by_at)
    linked = {a for ats in requirements.values() for a in ats}
    all_at = sorted(set(acceptance) | linked, key=lambda a: (a.rsplit("-", 1)[0], int(a.rsplit("-", 1)[1])))

    gaps: list[str] = []
    for req, ats in requirements.items():
        if not ats:
            gaps.append(f"{req}: links no acceptance test")
    status: dict[str, str] = {}
    for at in all_at:
        tests = by_at.get(at, [])
        if not tests:
            status[at] = "no test"
        else:
            results = {t.result for t in tests}
            status[at] = "passed" if results == {"passed"} else ", ".join(sorted(results - {"passed"}))
        if status[at] != "passed":
            gaps.append(f"{at}: {status[at]}")
    for at in sorted(linked - set(acceptance)):
        gaps.append(f"{at}: linked in §30.1 but not defined in §28")

    out = [
        "# Traceability",
        "",
        "Generated by `make traceability` (`scripts/check_traceability.py`); do not edit.",
        "",
        f"- Requirements in SRS §30.1: {len(requirements)}",
        f"- Acceptance tests in SRS §28: {len(acceptance)}; linked from §30.1: {len(linked)}",
        f"- Tests carrying an AT-ID: {sum(len(v) for v in by_at.values())}",
        f"- JUnit reports read (oldest first; later results win): {', '.join(reports) or 'none'}",
        f"- Acceptance tests passing: {sum(1 for s in status.values() if s == 'passed')} of {len(status)}",
        "",
        "## Gaps",
        "",
    ]
    out += [f"- {g}" for g in gaps] or ["None."]
    out += ["", "## Acceptance tests", "", "| AT-ID | Result | Tests |", "|---|---|---|"]
    for at in all_at:
        tests = by_at.get(at, [])
        listing = "<br>".join(f"`{t.file.removeprefix('backend/tests/')}::{t.name}` ({t.result})" for t in tests)
        out.append(f"| {at} | {status[at]} | {listing or '—'} |")
    out += ["", "## Requirements", "", "| Requirement | Acceptance tests | Result |", "|---|---|---|"]
    for req, ats in requirements.items():
        result = "passed" if ats and all(status[a] == "passed" for a in ats) else "gap"
        out.append(f"| {req} | {', '.join(ats) or '—'} | {result} |")
    OUT.write_text("\n".join(out) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(gaps)} gap(s)")
    for g in gaps:
        print(f"  - {g}")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
