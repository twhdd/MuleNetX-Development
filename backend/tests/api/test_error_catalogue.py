"""docs/api-errors.md is generated from the error table and must be current (PLAN T45)."""

from pathlib import Path

from mulenetx.core.error_codes import ERRORS, catalogue_markdown

DOC = Path(__file__).resolve().parents[3] / "docs" / "api-errors.md"


def test_catalogue_is_current() -> None:
    assert DOC.read_text() == catalogue_markdown(), "run: cd backend && uv run python -m mulenetx.cli export-errors"


def test_catalogue_lists_every_code() -> None:
    text = DOC.read_text()
    assert all(f"`{code}`" in text for code in ERRORS)
