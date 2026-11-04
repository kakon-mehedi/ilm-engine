"""Rule-based validation (step `validate`, 02-architecture L15): structural checks on every record.

Checks, each reported with the number of items checked and the failures:
- `anchors`: every anchor's block exists, its `block_hash` matches and `text[start:end] == quote`;
- `ids_unique`: no ID is used twice across record types;
- `origin_present`: units, facts and relationships carry an origin, inferred ones `ai_generated`;
- `relation_endpoints`: relationship and work-relation endpoints exist;
- `dual_grammar`: a group closed by a dual ("ابنا …") has exactly two members;
- `numbering`: entry numbers run 1..N without gaps or duplicates;
- `traceable`: every unit and fact has at least one anchor.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.enrichment.models import Entity, KnowledgeUnit, Relationship, Work, WorkRelation
from ilm_engine.integrity.revision_diff import anchors_in
from ilm_engine.validation.evidence import anchor_status

DUAL_OPENINGS = ("ابنا", "ابنتا", "أخوان", "أختان")


@dataclass
class CheckResult:
    name: str
    checked: int = 0
    failures: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "checked": self.checked, "failures": self.failures}


@dataclass
class Records:
    units: list[KnowledgeUnit] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    works: list[Work] = field(default_factory=list)
    work_relations: list[WorkRelation] = field(default_factory=list)
    others: list[Any] = field(
        default_factory=list
    )  # annotations, citations, internal refs, sections, metadata, issues


def _ids(records: Records) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for unit in records.units:
        found.append(("unit", unit.unit_id))
        found += [("fact", fact.fact_id) for fact in unit.facts]
    found += [("entity", e.entity_id) for e in records.entities]
    found += [("relationship", r.relation_id) for r in records.relationships]
    found += [("work", w.work_id) for w in records.works]
    found += [("work_relation", r.relation_id) for r in records.work_relations]
    for item in records.others:
        for attribute in ("annotation_id", "citation_id", "internal_ref_id", "section_id", "issue_id"):
            if hasattr(item, attribute):
                found.append((attribute.removesuffix("_id"), getattr(item, attribute)))
    return found


def run_checks(book: CanonicalBook, records: Records) -> list[CheckResult]:
    anchors = CheckResult("anchors")
    for anchor in anchors_in(
        [records.units, records.entities, records.relationships, records.work_relations, records.others]
    ):
        anchors.checked += 1
        status = anchor_status(anchor, book.blocks.get(anchor.block_id))
        if status != "valid":
            anchors.failures.append({"block_id": anchor.block_id, "start": anchor.start, "status": status})

    ids = CheckResult("ids_unique")
    counted = Counter(identifier for _, identifier in _ids(records))
    ids.checked = len(counted)
    ids.failures = [
        {"id": identifier, "count": count} for identifier, count in sorted(counted.items()) if count > 1
    ]

    origin = CheckResult("origin_present")
    items: list[Any] = [*records.units, *(f for u in records.units for f in u.facts), *records.relationships]
    for item in items:
        origin.checked += 1
        inferred = getattr(item, "assertion", "stated") == "inferred"
        if not item.origin or (inferred and item.origin != "ai_generated"):
            origin.failures.append(
                {"id": getattr(item, "fact_id", None) or getattr(item, "relation_id", None) or item.unit_id}
            )

    endpoints = CheckResult("relation_endpoints")
    entity_ids = {e.entity_id for e in records.entities}
    work_ids = {w.work_id for w in records.works}
    for relation in records.relationships:
        endpoints.checked += 1
        missing = [e for e in (relation.subject_entity_id, relation.object_entity_id) if e not in entity_ids]
        if missing:
            endpoints.failures.append({"relation_id": relation.relation_id, "missing": missing})
    for work_relation in records.work_relations:
        endpoints.checked += 1
        missing = [
            w for w in (work_relation.subject_work_id, work_relation.object_work_id) if w not in work_ids
        ]
        if missing:
            endpoints.failures.append({"relation_id": work_relation.relation_id, "missing": missing})

    dual = CheckResult("dual_grammar")
    groups: dict[str, set[str]] = {}
    group_quote: dict[str, str] = {}
    for relation in records.relationships:
        if relation.attrs.group_id and relation.type == "sibling_of":
            groups.setdefault(relation.attrs.group_id, set()).update(
                {relation.subject_entity_id, relation.object_entity_id}
            )
            group_quote[relation.attrs.group_id] = relation.evidence[0].quote
    for group_id, members in groups.items():
        if group_quote[group_id].strip().startswith(DUAL_OPENINGS):
            dual.checked += 1
            if len(members) != 2:
                dual.failures.append({"group_id": group_id, "members": len(members)})

    numbering = CheckResult("numbering")
    numbers = [u.entry_no for u in records.units if u.entry_no is not None]
    numbering.checked = len(numbers)
    if numbers:
        expected = set(range(1, max(numbers) + 1))
        numbering.failures += [{"missing": n} for n in sorted(expected - set(numbers))]
        numbering.failures += [{"duplicate": n} for n, c in sorted(Counter(numbers).items()) if c > 1]

    traceable = CheckResult("traceable")
    for unit in records.units:
        traceable.checked += 1 + len(unit.facts)
        if not unit.anchors:
            traceable.failures.append({"unit_id": unit.unit_id})
        traceable.failures += [{"fact_id": f.fact_id} for f in unit.facts if not f.evidence]

    return [anchors, ids, origin, endpoints, dual, numbering, traceable]


def report(checks: list[CheckResult]) -> dict[str, Any]:
    return {
        "passed": all(check.passed for check in checks),
        "checks": [check.to_json() for check in checks],
        "counts": {check.name: check.checked for check in checks},
        "failures": {check.name: len(check.failures) for check in checks},
    }
