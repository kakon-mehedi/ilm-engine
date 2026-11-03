import pytest

from ilm_engine.config import load_config
from ilm_engine.validation.confidence import decide, score, threshold_for


@pytest.fixture(scope="module")
def config():
    return load_config()


def test_rule_fact_exact_valid(config):
    result = score(config, "rule")
    assert result.score == 0.95
    assert result.factors.model_dump() == {
        "base": 0.95,
        "evidence": 1.0,
        "schema": 1.0,
        "agreement": 1.0,
        "penalties": {},
    }


def test_llm_two_models_agree(config):
    assert score(config, "llm", agreement="agree").score == 0.90


def test_llm_single_model_goes_to_review(config):
    result = score(config, "llm")
    assert result.score == 0.75
    assert decide(config, result.score) == "pending_review"


def test_ambiguous_entity_penalty(config):
    result = score(config, "rule", penalties=["ambiguous_entity"])
    assert result.score == 0.76 and result.factors.penalties == {"ambiguous_entity": 0.8}


def test_several_penalties_multiply(config):
    result = score(config, "llm", agreement="agree", penalties=["ambiguous_entity", "ambiguous_quote"])
    assert result.score == round(0.75 * 1.2 * 0.8 * 0.9, 4)


def test_normalized_evidence_and_repaired_schema(config):
    assert score(config, "llm", evidence="normalized", schema="repaired", agreement="agree").score == round(
        0.75 * 0.9 * 0.9 * 1.2, 4
    )


def test_no_evidence_or_invalid_schema_is_zero(config):
    assert score(config, "llm", evidence="none").score == 0.0
    assert score(config, "rule", schema="invalid").score == 0.0


def test_judge_resolved(config):
    assert score(config, "llm", agreement="judge_resolved").score == round(0.75 * 0.9, 4)


def test_disagreement_is_flagged(config):
    result = score(config, "llm", agreement="disagree")
    assert result.disagreement is True and result.score == 0.75


def test_score_is_clamped(config):
    assert score(config, "rule", agreement="agree").score == 1.0  # 0.95 × 1.2


def test_unknown_penalty_rejected(config):
    with pytest.raises(ValueError, match="unknown confidence penalty"):
        score(config, "rule", penalties=["vibes"])


def test_thresholds_and_decision(config):
    assert threshold_for(config) == 0.80
    assert threshold_for(config, "fiqh_ruling") == 0.95
    assert decide(config, 0.95) == "auto_approved"
    assert decide(config, 0.90, category="fiqh_ruling") == "pending_review"
    assert decide(config, 0.95, sensitive=["hadith_grading"]) == "pending_review"
    assert decide(config, 0.80) == "auto_approved"
