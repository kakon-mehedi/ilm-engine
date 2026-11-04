"""The `validate` step: rule checks, sensitivity and one `ValidationResult` per item (02-architecture L15).

Sensitive content in a unit's text or notes (T-104) puts the unit, and facts evidenced in a tagged
block, into scholar review whatever their confidence. Every unit, fact, entity and relationship gets a
`ValidationResult` with its confidence factors, the applied threshold and the decision.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.config import Config
from ilm_engine.enrichment.models import Issue, KnowledgeUnit, ValidationResult
from ilm_engine.validation.confidence import decide, score, threshold_for
from ilm_engine.validation.rules import Records, report, run_checks
from ilm_engine.validation.sensitivity import categories, enforce, sensitive_issue, tag_block


@dataclass
class Validation:
    records: Records
    results: list[ValidationResult]
    issues: list[Issue]
    rules: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        decisions: dict[str, int] = {}
        for result in self.results:
            decisions[result.decision] = decisions.get(result.decision, 0) + 1
        return {"rules": self.rules, "results": self.results, "decisions": dict(sorted(decisions.items()))}


def _result(config: Config, kind: str, target: str, item: Any, sensitive: Sequence[str]) -> ValidationResult:
    method = getattr(item.provenance, "method", "rule")
    base = "llm" if method in ("llm", "llm_consensus") else "rule"
    agreement = "agree" if method == "llm_consensus" else "single"
    factors = score(config, base, agreement=agreement).factors  # type: ignore[arg-type]
    threshold = threshold_for(config)
    return ValidationResult(
        target_kind=kind,
        target_id=target,
        schema_valid=True,
        evidence_found=True,
        evidence_match="exact",
        agreement=agreement,  # type: ignore[arg-type]
        factors=factors,
        confidence=item.confidence,
        sensitive=sorted(set(sensitive)),  # type: ignore[arg-type]
        threshold=threshold,
        decision=enforce(decide(config, item.confidence), sensitive),
    )


def validate(book: CanonicalBook, records: Records, config: Config, genres: list[str]) -> Validation:
    pub_ref = book.book.pub_ref
    scan = {(p.volume, p.n): p.scan_page for p in book.pages}
    issues: list[Issue] = []
    results: list[ValidationResult] = []
    units: list[KnowledgeUnit] = []
    annotations = {a.annotation_id: a for a in records.others if hasattr(a, "annotation_id")}

    for unit in records.units:
        blocks = {a.block_id for a in unit.anchors}
        for (
            annotation_id
        ) in unit.note_annotation_ids:  # every footnote of the entry (takhrij gradings live there)
            if annotation_id in annotations:
                blocks.update(annotations[annotation_id].target_block_ids)
        if unit.payload.get("tarjama_annotation"):
            blocks.add(unit.payload["tarjama_annotation"])
        tags = [
            tag
            for block_id in sorted(blocks)
            for tag in tag_block(
                book.block(block_id),
                pub_ref,
                scan[(book.block(block_id).volume, book.block(block_id).page)],
                genres,
            )
        ]
        unit_sensitive = categories(tags)
        facts = []
        for fact in unit.facts:
            fact_sensitive = sorted(
                {
                    *fact.sensitive,
                    *(
                        t.category
                        for t in tags
                        if t.anchor and t.anchor.block_id == fact.evidence[0].block_id
                    ),
                }
            )
            checked_fact = fact.model_copy(
                update={
                    "sensitive": fact_sensitive,
                    "review_status": enforce(fact.review_status, fact_sensitive),
                }
            )
            facts.append(checked_fact)
            results.append(_result(config, "fact", fact.fact_id, checked_fact, fact_sensitive))
        unit = unit.model_copy(
            update={"facts": facts, "review_status": enforce(unit.review_status, unit_sensitive)}
        )
        if unit_sensitive:
            issue = sensitive_issue(
                pub_ref, "unit", unit.unit_id, unit_sensitive, [t.anchor for t in tags if t.anchor]
            )
            issues.append(issue)
            unit = unit.model_copy(update={"issues": sorted({*unit.issues, issue.issue_id})})
        units.append(unit)
        results.append(_result(config, "unit", unit.unit_id, unit, unit_sensitive))

    for entity in records.entities:
        flagged = ["narrator_disambiguation"] if entity.disambiguation == "ambiguous" else []
        results.append(_result(config, "entity", entity.entity_id, entity, flagged))
    for relation in records.relationships:
        results.append(
            _result(config, "relationship", relation.relation_id, relation, list(relation.sensitive))
        )

    validated = Records(
        units, records.entities, records.relationships, records.works, records.work_relations, records.others
    )
    checks = run_checks(book, validated)
    return Validation(validated, results, issues, report(checks))
