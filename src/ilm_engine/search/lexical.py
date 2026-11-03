"""Normalized lexical search (step `search_index`, FR-112; OpenSearch in production).

An inverted index of normalized tokens (ADR-012, `search` profile) over every block, every knowledge
unit and every entity name, scored with BM25. Because queries are normalized the same way, spelling
and diacritic variants ("الدارقطني" / "الدَّارقطني") give identical results; every hit carries an anchor
into the original text for highlighting. Units are boosted so a person's entry ranks above the raw block
with the same words.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.enrichment.models import Anchor, Entity
from ilm_engine.nlp.normalize import NORMALIZER_VERSION, normalize

INDEX_VERSION = "1.0"
K1, B = 1.2, 0.75
KIND_BOOST = {"unit": 1.5, "entity": 1.3, "block": 1.0}
_TOKEN = re.compile(r"<SAW>|[ء-ي0-9A-Za-z]+")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(normalize(text, "search"))


class IndexedUnit(Protocol):
    """What the index needs from a unit (a `KnowledgeUnit`, or a record rebuilt from the database)."""

    unit_id: str
    payload: dict[str, Any]
    anchors: list[Anchor]


@dataclass(frozen=True)
class Hit:
    doc_id: str
    kind: str
    score: float
    anchor: dict[str, Any] | None


def build_index(
    book: CanonicalBook, units: Sequence[IndexedUnit], entities: Sequence[Entity] = ()
) -> dict[str, Any]:
    """The JSON-ready index (`search_index.json`)."""
    scan = {(p.volume, p.n): p.scan_page for p in book.pages}
    docs: list[dict[str, Any]] = []
    texts: list[list[str]] = []

    def add(doc_id: str, kind: str, text: str, anchor: Anchor | None, title: str | None = None) -> None:
        found = tokens(text)
        if not found:
            return
        docs.append(
            {
                "doc_id": doc_id,
                "kind": kind,
                "title": title,
                "length": len(found),
                "anchor": anchor.model_dump(mode="json") if anchor else None,
            }
        )
        texts.append(found)

    for block in book.blocks_in_order():
        anchor = Anchor(
            pub_ref=book.book.pub_ref,
            page=block.page,
            scan_page=scan[(block.volume, block.page)],
            block_id=block.block_id,
            start=0,
            end=len(block.text),
            quote=block.text[:120],
            quote_truncated=len(block.text) > 120,
            block_hash=block.block_hash,
        )
        add(block.block_id, "block", block.text, anchor)
    for unit in sorted(
        units, key=lambda u: u.unit_id
    ):  # sorted: byte-identical when rebuilt from the database
        person = unit.payload.get("person", {}).get("surface", "")
        add(
            unit.unit_id,
            "unit",
            " ".join([person, *(a.quote for a in unit.anchors)]),
            unit.anchors[0],
            person or None,
        )
    for entity in sorted(entities, key=lambda e: e.entity_id):
        names = " ".join([entity.canonical_name, *entity.aliases])
        add(
            entity.entity_id,
            "entity",
            names,
            entity.mentions[0] if entity.mentions else None,
            entity.canonical_name,
        )

    postings: dict[str, list[list[int]]] = {}
    for index, found in enumerate(texts):
        for token, count in sorted(Counter(found).items()):
            postings.setdefault(token, []).append([index, count])
    lengths = [doc["length"] for doc in docs]
    return {
        "version": INDEX_VERSION,
        "normalizer_version": NORMALIZER_VERSION,
        "pub_ref": book.book.pub_ref,
        "documents": docs,
        "avg_length": round(sum(lengths) / len(lengths), 4) if lengths else 0.0,
        "postings": dict(sorted(postings.items())),
    }


def search(index: dict[str, Any], query: str, limit: int = 10, kinds: set[str] | None = None) -> list[Hit]:
    """BM25 hits for `query`, best first (ties: units, entities, blocks; then document order)."""
    docs = index["documents"]
    total, avg = len(docs), index["avg_length"] or 1.0
    scores: dict[int, float] = {}
    for token in dict.fromkeys(tokens(query)):
        posting = index["postings"].get(token, [])
        if not posting:
            continue
        idf = math.log(1 + (total - len(posting) + 0.5) / (len(posting) + 0.5))
        for doc_index, frequency in posting:
            length = docs[doc_index]["length"]
            tf = frequency * (K1 + 1) / (frequency + K1 * (1 - B + B * length / avg))
            scores[doc_index] = scores.get(doc_index, 0.0) + idf * tf
    order = {"unit": 0, "entity": 1, "block": 2}
    ranked = sorted(
        (
            (round(score * KIND_BOOST.get(docs[i]["kind"], 1.0), 6), i)
            for i, score in scores.items()
            if kinds is None or docs[i]["kind"] in kinds
        ),
        key=lambda item: (-item[0], order.get(docs[item[1]]["kind"], 3), item[1]),
    )
    return [Hit(docs[i]["doc_id"], docs[i]["kind"], score, docs[i]["anchor"]) for score, i in ranked[:limit]]
