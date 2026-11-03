"""Confidence scoring (DECISIONS §8, ADR-008).

    confidence = clamp01(base × evidence × schema × agreement × penalties)

Every factor comes from `config.confidence`; the result carries its breakdown (`ConfidenceFactors`) so
reviewers can see why an item scored as it did. Items at or above the threshold of their category are
auto-approved unless sensitive (sensitive categories always go to review, T-104).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from ilm_engine.config import Config
from ilm_engine.enrichment.models import ConfidenceFactors, ReviewStatus

Base = Literal["rule", "structural", "llm"]
EvidenceMatch = Literal["exact", "normalized", "none"]
SchemaState = Literal["valid", "repaired", "invalid"]
Agreement = Literal["agree", "judge_resolved", "single", "disagree"]


@dataclass(frozen=True)
class Confidence:
    score: float
    factors: ConfidenceFactors
    disagreement: bool = False  # models disagreed and nobody resolved it → issue model_disagreement


def score(
    config: Config,
    base: Base,
    evidence: EvidenceMatch = "exact",
    schema: SchemaState = "valid",
    agreement: Agreement = "single",
    penalties: Iterable[str] = (),
) -> Confidence:
    """Confidence of one item from how it was produced and validated."""
    factors = config.confidence
    base_factor = factors.base.llm if base == "llm" else factors.base.rule
    evidence_factor = getattr(factors.evidence, evidence)
    schema_factor = getattr(factors.schema_, schema)
    # An unresolved disagreement keeps the single-model factor; the item goes to review via the issue.
    agreement_factor = (
        factors.agreement.single if agreement == "disagree" else getattr(factors.agreement, agreement)
    )

    applied: dict[str, float] = {}
    for name in sorted(set(penalties)):
        if name not in type(factors.penalties).model_fields:
            raise ValueError(f"unknown confidence penalty {name!r}")
        applied[name] = getattr(factors.penalties, name)

    product = base_factor * evidence_factor * schema_factor * agreement_factor
    for value in applied.values():
        product *= value
    return Confidence(
        score=round(min(1.0, max(0.0, product)), 4),
        factors=ConfidenceFactors.model_validate(
            {
                "base": base_factor,
                "evidence": evidence_factor,
                "schema": schema_factor,
                "agreement": agreement_factor,
                "penalties": applied,
            }
        ),
        disagreement=agreement == "disagree",
    )


def threshold_for(config: Config, category: str | None = None) -> float:
    """Auto-approve threshold of a category (`review.threshold.overrides`), else the default."""
    threshold = config.review.threshold
    return threshold.overrides.get(category, threshold.default) if category else threshold.default


def decide(
    config: Config, confidence: float, category: str | None = None, sensitive: Iterable[str] = ()
) -> ReviewStatus:
    """`auto_approved` if confident enough and not sensitive, else `pending_review`."""
    if list(sensitive) or confidence < threshold_for(config, category):
        return "pending_review"
    return "auto_approved"
