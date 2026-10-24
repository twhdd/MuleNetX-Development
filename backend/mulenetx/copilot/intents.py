"""Rule-based intent classification (SRS §21.3). Never uses the LLM; never grants permissions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

UNSUPPORTED = "UNSUPPORTED"


@cache
def table() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((Path(__file__).parent / "intents_v1.json").read_text(encoding="utf-8"))
    return data


@dataclass(frozen=True)
class Classification:
    intent: str
    reason: str | None = None


def classify(question: str, account_id: str | None, case_id: str | None, ring_id: str | None) -> Classification:
    t = table()
    q = question.lower()
    refs = {"account_id": account_id, "case_id": case_id, "ring_id": ring_id}
    chosen: str | None = None
    for intent in t["priority"]:
        if any(k in q for k in t["keywords"][intent]):
            chosen = intent
            break
    if chosen is None:
        chosen = "RING_SUMMARY" if ring_id else "CASE_SUMMARY" if case_id else "ACCOUNT_SUMMARY" if account_id else None
    if chosen is None:
        return Classification(UNSUPPORTED, "the question names no supported topic and no account, case or ring")
    # a keyword can point at a different subject than the one referenced: prefer what was referenced
    if not refs[t["subject"][chosen]]:
        fallback = "RING_SUMMARY" if ring_id else "CASE_SUMMARY" if case_id else None
        if fallback and refs[t["subject"][fallback]]:
            return Classification(fallback)
        return Classification(UNSUPPORTED, f"{chosen} needs {t['subject'][chosen]}")
    return Classification(chosen)


def sections(intent: str) -> list[str]:
    result: list[str] = table()["sections"].get(intent, [])
    return result
