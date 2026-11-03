import json

import pytest

from ilm_engine.config import load_config
from ilm_engine.extractors.llm_extract import UnitInput, extract_unit_facts
from ilm_engine.llm.gateway import LLMGateway
from ilm_engine.llm.providers.base import ProviderResponse
from ilm_engine.validation.consensus import comparable, reconcile

ORIGINS = {"b000135": "author_text", "b000134": "author_text"}
SCAN = {"b000135": 25, "b000134": 25}


class Fake:
    name = "fake"

    def __init__(self, text, model):
        self.text, self.default_model, self.calls = text, model, 0

    def complete(self, request):
        self.calls += 1
        return ProviderResponse(self.text, self.default_model)


def facts_json(*facts):
    return json.dumps({"facts": list(facts)}, ensure_ascii=False)


def birth(year, quote="أسلمت"):
    return {
        "predicate": "birth_year_hijri",
        "object": year,
        "evidence": [{"block_id": "b000135", "quote": quote}],
    }


@pytest.fixture(scope="module")
def unit(sample_book):
    return UnitInput(
        "ku_000000000008",
        sample_book.book.pub_ref,
        [sample_book.block("b000135")],
        [],
        sample_book.block("b000134"),
    )


def run(unit, a, b, judge=None):
    config = load_config()
    outcome = extract_unit_facts(
        LLMGateway(Fake(a, "claude-sonnet-5-5")),
        unit,
        config,
        ORIGINS,
        SCAN,
        verifier=LLMGateway(Fake(b, "openai/verifier")),
    )
    return reconcile(outcome.facts, outcome.result, outcome.verifier, unit, config, SCAN, judge=judge)


def test_agreement_multiplies_by_1_2(unit):
    result = run(unit, facts_json(birth(1200)), facts_json(birth(1200)))
    [item] = result.facts
    assert item.agreement == "agree" and item.fact.confidence == 0.9
    assert item.fact.review_status == "auto_approved" and item.fact.provenance.method == "llm_consensus"
    assert result.issues == []


def test_disagreement_goes_to_review(unit):
    result = run(unit, facts_json(birth(1200)), facts_json(birth(1205)))
    [item] = result.facts
    assert item.agreement == "disagree" and item.fact.review_status == "pending_review"
    assert item.fact.confidence == 0.75 and item.fact.object == 1200  # proposed, not approved
    [issue] = result.issues
    assert issue.code == "model_disagreement" and issue.target_id == item.fact.fact_id
    assert issue.details["model_outputs"] == [
        {"model_id": "claude-sonnet-5-5", "value": 1200},
        {"model_id": "openai/verifier", "value": 1205},
    ]


def test_both_outputs_kept_for_reviewer(unit):
    item = run(unit, facts_json(birth(1200)), facts_json(birth(1205))).facts[0]
    assert [output["value"] for output in item.model_outputs] == [1200, 1205]


def test_judge_with_evidence_resolves(unit):
    verdict = json.dumps(
        {"chosen": "b", "value": 1205, "evidence": [{"block_id": "b000135", "quote": "وتزوجت"}]}
    )
    judge = LLMGateway(Fake(verdict, "claude-opus-5-5"))
    item = run(unit, facts_json(birth(1200)), facts_json(birth(1205)), judge=judge).facts[0]
    assert item.agreement == "judge_resolved" and item.fact.object == 1205
    assert item.fact.confidence == round(0.75 * 0.9, 4) and item.fact.evidence[0].quote == "وتزوجت"


def test_judge_without_located_evidence_does_not_resolve(unit):
    verdict = json.dumps(
        {"chosen": "b", "value": 1205, "evidence": [{"block_id": "b000135", "quote": "ولد سنة ١٢٠٥"}]}
    )
    result = run(
        unit, facts_json(birth(1200)), facts_json(birth(1205)), judge=LLMGateway(Fake(verdict, "judge"))
    )
    assert result.facts[0].agreement == "disagree" and result.issues[0].code == "model_disagreement"


def test_fact_missing_from_verifier_is_single(unit):
    item = run(unit, facts_json(birth(1200)), facts_json()).facts[0]
    assert item.agreement == "single" and item.fact.confidence == 0.75


def test_no_verifier_is_single(unit, sample_book):
    config = load_config()
    outcome = extract_unit_facts(LLMGateway(Fake(facts_json(birth(1200)), "m")), unit, config, ORIGINS, SCAN)
    result = reconcile(outcome.facts, outcome.result, None, unit, config, SCAN)
    assert [item.agreement for item in result.facts] == ["single"]


def test_values_compared_after_normalization():
    assert comparable("اللَّه") == comparable("الله")
    assert comparable("١٢٠٠") == comparable(1200) == comparable("1200")
    assert comparable(True) != comparable("true")
