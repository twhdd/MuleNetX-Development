"""Deny-list vectors (SRS §21.6, §27.6): each baseline entry causes rejection in every text field, in any case;
the same words quoted verbatim from the context do not; a quotation that is not in the context does."""

import json
import re

import pytest

from mulenetx.copilot.validation import deny_list, validate
from tests.openapiutil import SRS

REFS = {"account:x:A"}
FIELDS = ("facts", "observed_signals", "possible_interpretation", "limitations")


def srs_baseline() -> tuple[str, ...]:
    line = next(x for x in SRS.read_text().splitlines() if "criminality-assertion deny-list" in x)
    return tuple(re.findall(r'"([^"]+)"', line.split("baseline entries:", 1)[1].split(")", 1)[0]))


def answer(field: str, text: str) -> str:
    out: dict[str, object] = {
        "facts": [{"text": "Fact.", "refs": ["account:x:A"]}],
        "observed_signals": [],
        "possible_interpretation": [],
        "limitations": [],
        "source_references": ["account:x:A"],
    }
    if field == "limitations":
        out["limitations"] = [text]
    else:
        out[field] = [{"text": text, "refs": ["account:x:A"]}]
    return json.dumps(out)


def test_deny_list_is_the_srs_baseline() -> None:
    assert deny_list(1) == srs_baseline()
    assert len(deny_list(1)) == 10


@pytest.mark.parametrize("phrase", srs_baseline())
@pytest.mark.parametrize("field", FIELDS)
def test_each_phrase_rejected_in_every_field(phrase, field) -> None:
    for variant in (phrase, phrase.upper(), phrase.title()):
        verdict, out = validate(answer(field, f"The account {variant} here."), REFS, "{}", 1024, 10)
        assert (verdict.ok, verdict.rule, out) == (False, 4, None), (field, variant)


@pytest.mark.parametrize("phrase", srs_baseline())
def test_quoted_context_text_is_allowed(phrase) -> None:
    quote = f"A note says the holder {phrase} according to a caller"
    context = json.dumps({"findings": [{"description": quote}]})
    verdict, _ = validate(answer("facts", f'The finding records: "{quote}".'), REFS, context, 1024, 10)
    assert verdict.ok, verdict
    # the same quotation is the model's own claim when the context does not contain it
    verdict, _ = validate(answer("facts", f'The finding records: "{quote}".'), REFS, "{}", 1024, 10)
    assert (verdict.ok, verdict.rule) == (False, 4)
