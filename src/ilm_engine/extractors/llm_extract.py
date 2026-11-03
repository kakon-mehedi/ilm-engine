"""LLM fact extraction with mandatory evidence (ADR-007; the Genre Extractor's MVP form, DECISIONS §12).

The model sees only the blocks it may cite (the entry, its footnotes, its section heading) and must
quote its evidence verbatim. Every quote goes through the evidence guard: a fact whose quote is not in
the cited block is rejected with `evidence_not_found` and never stored. Accepted facts carry their
anchors, the answering model id and the prompt version.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ilm_engine.canonical.models import Block
from ilm_engine.config import Config
from ilm_engine.enrichment.issues import make_issue
from ilm_engine.enrichment.models import Anchor, Fact, Issue, Origin, Provenance
from ilm_engine.llm.gateway import LLMGateway, LLMResult
from ilm_engine.llm.prompts import load_prompt
from ilm_engine.validation.confidence import decide, score
from ilm_engine.validation.evidence import locate

STEP = "units"
TASK = "entry_facts"


class QuoteRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    block_id: str
    quote: str
    hint_start: int | None = None


class ExtractedFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    predicate: str
    object: Any
    evidence: list[QuoteRef] = Field(min_length=1)
    assertion: Literal["stated", "inferred"] = "stated"


class EntryFacts(BaseModel):
    """Output schema of the `entry_facts` prompt."""

    model_config = ConfigDict(extra="forbid")
    facts: list[ExtractedFact]


@dataclass(frozen=True)
class UnitInput:
    unit_id: str
    pub_ref: str
    entry: list[Block]
    footnotes: list[Block] = field(default_factory=list)
    heading: Block | None = None

    def blocks(self) -> list[Block]:
        return [*self.entry, *self.footnotes, *([self.heading] if self.heading else [])]

    def payload(self) -> dict[str, Any]:
        def view(block: Block) -> dict[str, str]:
            return {"block_id": block.block_id, "text": block.text}

        return {
            "unit_id": self.unit_id,
            "entry": [view(block) for block in self.entry],
            "footnotes": [view(block) for block in self.footnotes],
            "heading": view(self.heading) if self.heading else None,
        }


@dataclass
class ExtractionOutcome:
    facts: list[Fact]
    issues: list[Issue]
    result: LLMResult[EntryFacts] | None
    verifier: LLMResult[EntryFacts] | None = None
    rejected: list[ExtractedFact] = field(default_factory=list)


def _anchor_all(
    fact: ExtractedFact, unit: UnitInput, scan_pages: dict[str, int]
) -> tuple[list[Anchor], list[str], set[str], list[QuoteRef]] | None:
    """Anchors for every quote of `fact`, or None if any quote is not in its (allowed) block."""
    allowed = {block.block_id: block for block in unit.blocks()}
    anchors: list[Anchor] = []
    matches: list[str] = []
    penalties: set[str] = set()
    missing: list[QuoteRef] = []
    for ref in fact.evidence:
        block = allowed.get(ref.block_id)
        found = (
            locate(
                ref.quote,
                block,
                pub_ref=unit.pub_ref,
                scan_page=scan_pages[block.block_id],
                hint_start=ref.hint_start,
            )
            if block is not None
            else None
        )
        if found is None:
            missing.append(ref)
            continue
        anchors.append(found.anchor)
        matches.append(found.match)
        if found.ambiguity_penalty < 1:
            penalties.add("ambiguous_quote")
    if missing:
        return None
    return anchors, matches, penalties, missing


def extract_unit_facts(
    gateway: LLMGateway,
    unit: UnitInput,
    config: Config,
    origins: dict[str, Origin],
    scan_pages: dict[str, int],
    verifier: LLMGateway | None = None,
) -> ExtractionOutcome:
    """Run the extractor (and the verifier, if any) on one unit and keep only evidenced facts."""
    prompt = load_prompt(TASK)
    payload = unit.payload()
    result = gateway.complete_json(TASK, prompt.version, payload, EntryFacts, prompt=prompt.text)
    second = (
        verifier.complete_json(TASK, prompt.version, payload, EntryFacts, prompt=prompt.text)
        if verifier
        else None
    )

    if result.needs_llm:
        issue = make_issue(
            unit.pub_ref,
            "needs_llm",
            "info",
            "unit",
            unit.unit_id,
            f"LLM task {TASK!r} not run (no provider); facts beyond the rule-based ones need review.",
            STEP,
            details={"task": TASK},
        )
        return ExtractionOutcome([], [issue], result, second)
    if result.output is None:
        issue = make_issue(
            unit.pub_ref,
            "schema_invalid",
            "warning",
            "unit",
            unit.unit_id,
            f"{result.model} output for {TASK!r} failed schema validation after one repair.",
            STEP,
            details={"errors": result.errors, "model_id": result.model},
        )
        return ExtractionOutcome([], [issue], result, second)

    facts: list[Fact] = []
    issues: list[Issue] = []
    rejected: list[ExtractedFact] = []
    for extracted in result.output.facts:
        anchored = _anchor_all(extracted, unit, scan_pages)
        if anchored is None:
            rejected.append(extracted)
            quotes = [{"block_id": ref.block_id, "quote": ref.quote} for ref in extracted.evidence]
            issues.append(
                make_issue(
                    unit.pub_ref,
                    "evidence_not_found",
                    "warning",
                    "unit",
                    unit.unit_id,
                    f"Rejected {extracted.predicate!r} from {result.model}: quote not in the cited block.",
                    STEP,
                    details={"predicate": extracted.predicate, "evidence": quotes, "model_id": result.model},
                    key=f"{len(rejected)}",
                    method="llm",
                )
            )
            continue
        anchors, matches, penalties, _ = anchored
        inferred = extracted.assertion == "inferred"
        origin: Origin = "ai_generated" if inferred else origins.get(anchors[0].block_id, "author_text")
        confidence = score(
            config,
            "llm",
            evidence="normalized" if "normalized" in matches else "exact",
            schema="repaired" if result.repaired else "valid",
            penalties=sorted(penalties),
        )
        facts.append(
            Fact(
                fact_id=f"{unit.unit_id}#f{len(facts) + 1}",
                predicate=extracted.predicate,
                object=extracted.object,
                evidence=anchors,
                origin=origin,
                assertion=extracted.assertion,
                confidence=confidence.score,
                review_status=decide(config, confidence.score),
                provenance=Provenance(
                    method="llm",
                    step=STEP,
                    step_version="1.0.0",
                    model_id=result.model,
                    prompt_id=TASK,
                    prompt_version=prompt.version,
                ),
            )
        )
    return ExtractionOutcome(facts, issues, result, second, rejected)
