"""Output validation (SRS §21.6): any failure discards the answer with 503 AI_RESPONSE_INVALID."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class _Item(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str
    refs: list[str]


class _Answer(BaseModel):
    """The model-produced part of the §21.5 response (server-filled fields excluded)."""

    model_config = ConfigDict(extra="forbid", strict=True)
    facts: list[_Item]
    observed_signals: list[_Item]
    possible_interpretation: list[_Item]
    limitations: list[str]
    source_references: list[str]


TEXT_SECTIONS = ("facts", "observed_signals", "possible_interpretation")
QUOTE = re.compile(r"[\"“]([^\"”]+)[\"”]")


@cache
def deny_list(version: int = 1) -> tuple[str, ...]:
    path = Path(__file__).parent / f"deny_list_v{version}.txt"
    return tuple(line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


@dataclass(frozen=True)
class Verdict:
    ok: bool
    rule: int | None = None
    detail: str | None = None


def _texts(answer: dict[str, Any]) -> list[str]:
    out = [i.get("text", "") for s in TEXT_SECTIONS for i in answer.get(s, [])]
    return out + list(answer.get("limitations", []))


def _unquoted(text: str, context_text: str) -> str:
    """Remove quoted spans that match context text verbatim; deny-listed phrases inside them are quotations."""
    return QUOTE.sub(lambda m: "" if m.group(1) in context_text else m.group(0), text)


def validate(
    raw: str, refs: set[str], context_text: str, max_tokens: int, output_tokens: int | None, deny_version: int = 1
) -> tuple[Verdict, dict[str, Any] | None]:
    tokens = output_tokens if output_tokens is not None else math.ceil(len(raw) / 4)
    if tokens > max_tokens:
        return Verdict(False, 5, f"output of {tokens} tokens exceeds {max_tokens}"), None
    try:
        answer = _Answer.model_validate(json.loads(raw)).model_dump()
    except ValueError:  # json.JSONDecodeError and pydantic.ValidationError are both ValueErrors
        return Verdict(False, 1, "output does not parse against the schema"), None
    cited = [r for s in TEXT_SECTIONS for i in answer[s] for r in i["refs"]] + list(answer["source_references"])
    unknown = sorted({r for r in cited if r not in refs})
    if unknown:
        return Verdict(False, 2, f"{len(unknown)} reference(s) not in the context"), None
    for section in ("facts", "observed_signals"):
        if any(not item["refs"] for item in answer[section]):
            return Verdict(False, 3, f"an item of {section} cites no reference"), None
    phrases = deny_list(deny_version)
    for text in _texts(answer):
        lowered = _unquoted(text, context_text).lower()
        hit = next((p for p in phrases if p in lowered), None)
        if hit:
            return Verdict(False, 4, "criminality-assertion deny-list"), None
    return Verdict(True), answer
