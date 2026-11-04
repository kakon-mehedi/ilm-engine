"""Multi-model consensus (ADR-008; the Discrepancy Resolver's MVP form, DECISIONS §12).

The extractor's evidenced facts are compared field by field with an independent verifier (a different
model family): same predicate, same normalized value. Agreement multiplies confidence by
`confidence.agreement.agree`; a disagreement is never settled silently: an optional judge model must
pick a value with evidence that passes the evidence guard (`judge_resolved`), otherwise the fact goes to
review with issue `model_disagreement` and both outputs attached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from ilm_engine.config import Config
from ilm_engine.enrichment.issues import make_issue
from ilm_engine.enrichment.models import Fact, Issue
from ilm_engine.extractors.llm_extract import EntryFacts, ExtractedFact, QuoteRef, UnitInput
from ilm_engine.llm.gateway import LLMGateway, LLMResult
from ilm_engine.llm.prompts import load_prompt
from ilm_engine.nlp.normalize import normalize
from ilm_engine.validation.confidence import decide
from ilm_engine.validation.evidence import locate

STEP = "validate"
JUDGE_TASK = "judge"
Agreement = Literal["agree", "disagree", "judge_resolved", "single"]


class JudgeVerdict(BaseModel):
    """Output schema of the `judge` prompt."""

    model_config = ConfigDict(extra="forbid")
    value: Any = None
    chosen: Literal["a", "b"] | None = None
    evidence: list[QuoteRef] = []
    reason: str | None = None


@dataclass
class FactConsensus:
    fact: Fact
    agreement: Agreement
    model_outputs: list[dict[str, Any]]  # [{model_id, value}] shown to reviewers


@dataclass
class ConsensusOutcome:
    facts: list[FactConsensus]
    issues: list[Issue] = field(default_factory=list)


def comparable(value: Any) -> Any:
    """Value form for comparison: strings normalized (ADR-012), numbers as numbers."""
    if isinstance(value, str):
        stripped = value.strip()
        try:
            return float(normalize(stripped))
        except ValueError:
            return normalize(stripped)
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, list):
        return [comparable(item) for item in value]
    if isinstance(value, dict):
        return {key: comparable(item) for key, item in sorted(value.items())}
    return value


def _rescale(config: Config, confidence: float, agreement: Agreement) -> float:
    """Swap the single-model agreement factor for `agreement` in an existing score."""
    factors = config.confidence.agreement
    target = {"agree": factors.agree, "judge_resolved": factors.judge_resolved}.get(agreement, factors.single)
    return round(min(1.0, max(0.0, confidence / factors.single * target)), 4)


def reconcile(
    facts: list[Fact],
    primary: LLMResult[EntryFacts],
    verifier: LLMResult[EntryFacts] | None,
    unit: UnitInput,
    config: Config,
    scan_pages: dict[str, int],
    judge: LLMGateway | None = None,
) -> ConsensusOutcome:
    """Apply verifier agreement (and the judge) to the extractor's evidenced `facts` of one unit."""
    if verifier is None or verifier.output is None:
        return ConsensusOutcome(
            [
                FactConsensus(fact, "single", [{"model_id": primary.model, "value": fact.object}])
                for fact in facts
            ]
        )

    by_predicate: dict[str, list[ExtractedFact]] = {}
    for extracted in verifier.output.facts:
        by_predicate.setdefault(extracted.predicate, []).append(extracted)

    results: list[FactConsensus] = []
    issues: list[Issue] = []
    for fact in facts:
        outputs = [{"model_id": primary.model, "value": fact.object}]
        others = by_predicate.get(fact.predicate, [])
        outputs += [{"model_id": verifier.model, "value": other.object} for other in others]
        if not others:
            results.append(FactConsensus(fact, "single", outputs))
            continue
        if any(comparable(other.object) == comparable(fact.object) for other in others):
            confidence = _rescale(config, fact.confidence, "agree")
            agreed = fact.model_copy(
                update={
                    "confidence": confidence,
                    "review_status": decide(config, confidence, sensitive=fact.sensitive),
                    "provenance": fact.provenance.model_copy(update={"method": "llm_consensus"}),
                }
            )
            results.append(FactConsensus(agreed, "agree", outputs))
            continue

        resolved = _judge(judge, fact, others[0], primary, verifier, unit, scan_pages) if judge else None
        if resolved is not None:
            value, anchors = resolved
            confidence = _rescale(config, fact.confidence, "judge_resolved")
            judged = fact.model_copy(
                update={
                    "object": value,
                    "evidence": anchors,
                    "confidence": confidence,
                    "review_status": decide(config, confidence, sensitive=fact.sensitive),
                    "provenance": fact.provenance.model_copy(update={"method": "llm_consensus"}),
                }
            )
            results.append(FactConsensus(judged, "judge_resolved", outputs))
            continue

        issues.append(
            make_issue(
                unit.pub_ref,
                "model_disagreement",
                "warning",
                "fact",
                fact.fact_id,
                f"{primary.model} and {verifier.model} disagree on {fact.predicate!r}; both go to review.",
                STEP,
                details={"predicate": fact.predicate, "model_outputs": outputs},
                anchors=fact.evidence,
                method="llm_consensus",
            )
        )
        results.append(
            FactConsensus(fact.model_copy(update={"review_status": "pending_review"}), "disagree", outputs)
        )
    return ConsensusOutcome(results, issues)


def _judge(
    judge: LLMGateway,
    fact: Fact,
    other: ExtractedFact,
    primary: LLMResult[EntryFacts],
    verifier: LLMResult[EntryFacts],
    unit: UnitInput,
    scan_pages: dict[str, int],
) -> tuple[Any, list] | None:
    """The judge's value with located evidence, or None when it cannot settle the disagreement."""
    prompt = load_prompt(JUDGE_TASK)
    payload = {
        "field": fact.predicate,
        "source_blocks": unit.payload(),
        "a": {"model_id": primary.model, "value": fact.object, "evidence": [a.quote for a in fact.evidence]},
        "b": {
            "model_id": verifier.model,
            "value": other.object,
            "evidence": [e.quote for e in other.evidence],
        },
    }
    result = judge.complete_json(JUDGE_TASK, prompt.version, payload, JudgeVerdict, prompt=prompt.text)
    verdict = result.output
    if verdict is None or verdict.chosen is None or not verdict.evidence:
        return None
    allowed = {block.block_id: block for block in unit.blocks()}
    anchors = []
    for ref in verdict.evidence:
        block = allowed.get(ref.block_id)
        found = (
            locate(ref.quote, block, pub_ref=unit.pub_ref, scan_page=scan_pages[block.block_id])
            if block is not None
            else None
        )
        if found is None:
            return None  # an unevidenced verdict does not settle anything
        anchors.append(found.anchor)
    value = fact.object if verdict.chosen == "a" else other.object
    return value, anchors
