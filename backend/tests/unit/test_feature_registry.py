"""Feature registry v1 integrity (SRS §10.1, §10.5)."""

import hashlib
import re
from pathlib import Path

from mulenetx.features.registry import REGISTRY_FILE, load

SRS = Path(__file__).resolve().parents[3] / "docs" / "SRS.md"
FIELDS = {
    "id",
    "name",
    "definition",
    "window",
    "window_seconds",
    "unavailable_when",
    "cold_start",
    "description",
    "datatype",
    "unit",
    "direction",
    "cap",
    "leakage_risk",
    "group",
}


def _srs_rows() -> list[tuple[str, str, str, str]]:
    text = SRS.read_text(encoding="utf-8")
    section = text[text.index("## 10.1 Normative Feature Registry") : text.index("## 10.2 ")]
    rows = []
    for line in section.splitlines():
        m = re.match(r"^\| (F\d\d) \| ([a-z0-9_]+) \| (.*) \| (.*) \| (.*) \| (.*) \|$", line)
        if m:
            rows.append((m.group(1), m.group(2), m.group(5).strip(), m.group(6).strip()))
    return rows


def test_registry_matches_srs_identities() -> None:
    reg = load()
    srs = _srs_rows()
    assert len(srs) == 42 == len(reg.features)
    assert [(f.id, f.name) for f in reg.features] == [(r[0], r[1]) for r in srs]
    for f, (_, _, unavailable, cold) in zip(reg.features, srs, strict=True):
        assert f.unavailable_when == unavailable.replace("`", ""), f.id
        assert (f.cold_start == "UNAVAILABLE") == (cold == "UNAVAILABLE"), f.id


def test_every_entry_has_all_fields_and_caps() -> None:
    import json

    data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    assert all(set(entry) == FIELDS for entry in data["features"])
    reg = load()
    assert (reg.cap("F09"), reg.cap("F23"), reg.cap("F32")) == (1e6, 10.0, 100)
    assert reg.epsilon == 1e-9


def test_definition_hash_is_file_sha256() -> None:
    assert load().definition_hash == hashlib.sha256(REGISTRY_FILE.read_bytes()).hexdigest()
    assert load().feature_version == "v1"
