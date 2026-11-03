import json

import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.llm_extract import UnitInput, extract_unit_facts
from ilm_engine.llm.gateway import LLMGateway
from ilm_engine.llm.providers.base import ProviderResponse
from ilm_engine.llm.providers.null import NullProvider


class FakeProvider:
    name = "fake"

    def __init__(self, text, model="claude-sonnet-5-5"):
        self.text, self.default_model = text, model
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return ProviderResponse(self.text, self.default_model)


@pytest.fixture(scope="module")
def unit(sample_book):
    return UnitInput(
        unit_id="ku_000000000008",
        pub_ref=sample_book.book.pub_ref,
        entry=[sample_book.block("b000135")],
        footnotes=[sample_book.block("b000140")],
        heading=sample_book.block("b000134"),
    )


ORIGINS = {"b000135": "author_text", "b000140": "editor_footnote", "b000134": "author_text"}
SCAN = {"b000135": 25, "b000140": 25, "b000134": 25}


def answer(*facts):
    return json.dumps({"facts": list(facts)}, ensure_ascii=False)


def fact(predicate, obj, block_id, quote, **extra):
    return {
        "predicate": predicate,
        "object": obj,
        "evidence": [{"block_id": block_id, "quote": quote}],
        **extra,
    }


def run(provider, unit, **kwargs):
    return extract_unit_facts(LLMGateway(provider), unit, load_config(), ORIGINS, SCAN, **kwargs)


def test_hallucinated_quote_rejected_with_issue(unit):
    provider = FakeProvider(
        answer(
            fact("converted_to_islam", True, "b000135", "أسلمت"),
            fact("birth_place", "مكة", "b000135", "ولدت في مكة"),
        )
    )
    outcome = run(provider, unit)
    assert [f.predicate for f in outcome.facts] == ["converted_to_islam"]
    [issue] = outcome.issues
    assert issue.code == "evidence_not_found" and issue.target_id == "ku_000000000008"
    assert issue.details["evidence"] == [{"block_id": "b000135", "quote": "ولدت في مكة"}]
    assert [r.predicate for r in outcome.rejected] == ["birth_place"]


def test_accepted_fact_carries_model_prompt_and_anchors(unit):
    outcome = run(FakeProvider(answer(fact("has_narration", False, "b000135", "ولم يُروَ عنها شيءٌ"))), unit)
    [accepted] = outcome.facts
    assert accepted.fact_id == "ku_000000000008#f1"
    assert accepted.provenance.model_id == "claude-sonnet-5-5"
    assert (accepted.provenance.prompt_id, accepted.provenance.prompt_version) == ("entry_facts", "v1")
    [anchor] = accepted.evidence
    assert (anchor.block_id, anchor.start, anchor.end) == ("b000135", 78, 97)
    assert accepted.origin == "author_text" and accepted.assertion == "stated"
    assert accepted.confidence == 0.75 and accepted.review_status == "pending_review"


def test_quote_from_a_block_not_given_is_rejected(unit, sample_book):
    other = sample_book.block("b000109")
    outcome = run(FakeProvider(answer(fact("married_to", "علي", "b000109", other.text[37:77]))), unit)
    assert outcome.facts == [] and outcome.issues[0].code == "evidence_not_found"


def test_normalized_quote_accepted_with_lower_confidence(unit):
    outcome = run(FakeProvider(answer(fact("converted_to_islam", True, "b000135", "اسلمت"))), unit)
    assert outcome.facts[0].confidence == round(0.75 * 0.9, 4)
    assert outcome.facts[0].evidence[0].quote == "أسلمت"


def test_footnote_fact_has_editor_origin(unit, sample_book):
    quote = sample_book.block("b000140").text[:12]
    outcome = run(FakeProvider(answer(fact("note", "x", "b000140", quote))), unit)
    assert outcome.facts[0].origin == "editor_footnote"


def test_inferred_fact_is_ai_generated(unit):
    provider = FakeProvider(
        answer(fact("child_of", "رسول الله", "b000134", "أولاد رسول اللَّه", assertion="inferred"))
    )
    outcome = run(provider, unit)
    assert outcome.facts[0].origin == "ai_generated" and outcome.facts[0].assertion == "inferred"


def test_model_only_sees_allowed_blocks(unit):
    provider = FakeProvider(answer())
    run(provider, unit)
    payload = provider.requests[0].input
    assert [b["block_id"] for b in payload["entry"]] == ["b000135"] and payload["heading"][
        "block_id"
    ] == "b000134"
    assert (
        "verbatim" in provider.requests[0].prompt or "character for character" in provider.requests[0].prompt
    )


def test_null_provider_gives_needs_llm(unit):
    outcome = run(NullProvider(), unit)
    assert outcome.facts == [] and [i.code for i in outcome.issues] == ["needs_llm"]


def test_invalid_output_gives_schema_invalid(unit):
    outcome = run(FakeProvider('{"facts": "none"}'), unit)
    assert [i.code for i in outcome.issues] == ["schema_invalid"]


def test_verifier_runs_independently(unit):
    verifier = FakeProvider(
        answer(fact("converted_to_islam", True, "b000135", "أسلمت")), model="openai/verifier"
    )
    outcome = run(FakeProvider(answer()), unit, verifier=LLMGateway(verifier))
    assert outcome.verifier.model == "openai/verifier" and len(verifier.requests) == 1
