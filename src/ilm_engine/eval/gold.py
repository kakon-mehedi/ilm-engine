"""Entity evaluation against the editor's printed index (FR-120; gold data in `eval/`, T-130).

The gold sample lists each biographical entry's number and the subject's name as printed in
فهرس الرواة المترجم لهم. For each gold row the extracted unit with that entry number gives the subject
entity; it matches when the ism (or kunya) agrees after normalization (diacritics, joined compounds such
as "عبدالله", the ﷺ honorific). Where both sides give a lineage, `chain_agreement` checks the first
ancestor too. Precision is over the extracted entry subjects, recall over the gold rows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ilm_engine.enrichment.models import Enrichment
from ilm_engine.nlp.nasab import parse_name
from ilm_engine.nlp.normalize import normalize

DEFAULT_GOLD = Path(__file__).resolve().parents[3] / "eval" / "gold_index_sample.json"


def _key(text: str | None) -> str:
    return normalize((text or "").replace("ﷺ", " ")).replace("<SAW>", "").replace(" ", "")


def _first_name(text: str) -> tuple[str, str | None]:
    """(ism or kunya, first ancestor) of a printed index name."""
    parsed = parse_name(text.replace("ﷺ", " "))
    if parsed is None:
        return _key(text), None
    return _key(parsed.ism or parsed.kunya), (_key(parsed.chain[0]) if parsed.chain else None)


def evaluate(enrichment: Enrichment, gold: dict[str, Any]) -> dict[str, Any]:
    entities = {entity.entity_id: entity for entity in enrichment.entities}
    by_entry = {unit.entry_no: unit for unit in enrichment.knowledge_units if unit.entry_no is not None}
    matched, missed, chains, chain_checks = [], [], 0, 0
    correct_units: set[str] = set()
    for row in gold["entries"]:
        unit = by_entry.get(row["entry_no"])
        entity = entities.get(unit.subject_entity_id) if unit and unit.subject_entity_id else None
        gold_name, gold_parent = _first_name(row["name"])
        name = entity.name if entity else None
        extracted = _key(name.ism or name.kunya) if name else ""
        if entity is None or extracted != gold_name:
            missed.append(
                {
                    "entry_no": row["entry_no"],
                    "gold": row["name"],
                    "extracted": entity.canonical_name if entity else None,
                }
            )
            continue
        matched.append(row["entry_no"])
        correct_units.add(unit.unit_id)  # type: ignore[union-attr]
        if gold_parent and name and name.nasab:
            chain_checks += 1
            # The index may name the father by kunya ("بن أبي هالة") where the lineage has his ism ("مالك").
            chains += _key(name.nasab[0]) == gold_parent or gold_parent in _key(entity.canonical_name)
    predicted = [u for u in enrichment.knowledge_units if u.subject_entity_id]
    false_positives = [
        {"entry_no": u.entry_no, "extracted": entities[u.subject_entity_id].canonical_name}  # type: ignore[index]
        for u in predicted
        if u.unit_id not in correct_units and u.subject_entity_id in entities
    ]
    precision = len(correct_units) / len(predicted) if predicted else 0.0
    recall = len(matched) / len(gold["entries"]) if gold["entries"] else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "pub_ref": enrichment.pub_ref,
        "gold": {
            "source": gold.get("source"),
            "pdf_pages": gold.get("pdf_pages"),
            "entries": len(gold["entries"]),
        },
        "predicted": len(predicted),
        "matched": len(matched),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "chain_agreement": {
            "checked": chain_checks,
            "agree": chains,
            "rate": round(chains / chain_checks, 4) if chain_checks else None,
        },
        "missed": missed,
        "false_positives": false_positives,
    }


def load_gold(path: Path = DEFAULT_GOLD) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
