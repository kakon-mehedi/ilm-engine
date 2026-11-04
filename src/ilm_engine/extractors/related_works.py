"""Related works / book family (step `related_works`, ADR-018; the Citation Resolver's MVP form).

- `cites`: one edge from this book to every work its citations resolve to (count aggregated).
- `same_topic_as`: works the editor names in the preface as other books he edited on the same subject
  ("حققت كتاب "…" لأبي داود …"), stated by the editor.
- `tahqiq_of`: the editor's own combined edition ("وسميته "…"") of those works.
- Title patterns (شرح / حاشية / مختصر / ترجمة) give candidate `sharh_of` / `hashiyah_of` /
  `mukhtasar_of` / `translation_of` edges, inferred and sent to review.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.config import Config
from ilm_engine.enrichment.models import Anchor, Origin, Provenance, Work, WorkRelation, WorkRelType
from ilm_engine.ids import make_id, natural_key
from ilm_engine.processors.citations import Citations, title_key, work_id
from ilm_engine.validation.confidence import decide, score

STEP = "related_works"
MAX_EVIDENCE = 5
_PROVENANCE = Provenance(method="rule", step=STEP, step_version="1.0.0")

_EDITED_WORK = re.compile(
    r'كتاب\s+["«](?P<title>[^"»]+)["»]\s*(?:ل(?:لإمام[ِ]?\s*)?(?P<author>[^،.]+?))?(?=[،.]|$)'
)
_EDITED = re.compile(r"حق[َّ]*ق[ْ]?ت")
_NAMED_EDITION = re.compile(r'وسميته\s+["«](?P<title>[^"»]+)["»]')
_TITLE_RELATIONS: list[tuple[re.Pattern[str], WorkRelType]] = [
    (re.compile(r"^شرح\s+(?P<base>.+)$"), "sharh_of"),
    (re.compile(r"^حاشية\s+(?:على\s+)?(?P<base>.+)$"), "hashiyah_of"),
    (re.compile(r"^مختصر\s+(?P<base>.+)$"), "mukhtasar_of"),
    (re.compile(r"^ترجمة\s+(?P<base>.+)$"), "translation_of"),
]


def title_relation(title: str) -> tuple[WorkRelType, str] | None:
    """`شرح صحيح البخاري` → (`sharh_of`, `صحيح البخاري`)."""
    for pattern, relation in _TITLE_RELATIONS:
        if match := pattern.match(title.strip()):
            return relation, match.group("base").strip()
    return None


@dataclass
class RelatedWorks:
    works: list[Work]
    relations: list[WorkRelation] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {"works": self.works, "work_relations": self.relations}


def _anchor(book: CanonicalBook, block_id: str, start: int, end: int) -> Anchor:
    block = book.block(block_id)
    return Anchor(
        pub_ref=book.book.pub_ref,
        page=block.page,
        scan_page=book.page(block.page, block.volume).scan_page,
        block_id=block_id,
        start=start,
        end=end,
        quote=block.text[start:end],
        block_hash=block.block_hash,
    )


def related_works(
    book: CanonicalBook, citations: Citations, origins: dict[str, Origin], config: Config
) -> RelatedWorks:
    pub_ref = book.book.pub_ref
    works = {work.work_id: work for work in citations.works}
    this = next(work for work in works.values() if work.status == "this_book")
    relations: list[WorkRelation] = []
    rule = score(config, "rule").score

    def relation(
        type_: WorkRelType,
        subject: str,
        obj: str,
        evidence: list[Anchor],
        origin: Origin,
        assertion: str = "stated",
        count: int = 1,
    ) -> WorkRelation:
        confidence = rule if assertion == "stated" else score(config, "llm").score
        return WorkRelation(
            relation_id=make_id("rel", pub_ref, natural_key(type_, subject, obj)),
            type=type_,
            subject_work_id=subject,
            object_work_id=obj,
            evidence=evidence,
            origin="ai_generated" if assertion == "inferred" else origin,
            assertion=assertion,  # type: ignore[arg-type]
            confidence=confidence,
            count=count,
            review_status=decide(config, confidence) if assertion == "stated" else "pending_review",
            provenance=_PROVENANCE,
        )

    cited: dict[str, list[Anchor]] = defaultdict(list)
    for citation in citations.citations:
        if citation.work_id and citation.work_id != this.work_id:
            cited[citation.work_id].append(citation.anchor)
    for target, anchors in sorted(cited.items()):
        relations.append(
            relation(
                "cites", this.work_id, target, anchors[:MAX_EVIDENCE], "editor_footnote", count=len(anchors)
            )
        )

    # The editor's preface: other books he edited on the topic, and his combined edition of them.
    for block in book.blocks_in_order():
        if origins.get(block.block_id) != "editor_text" or not _EDITED.search(block.text):
            continue
        edited: list[str] = []
        for match in _EDITED_WORK.finditer(block.text):
            title = match.group("title")
            if title_key(title) == this.title_normalized or work_id(title) == this.work_id:
                continue
            author = (match.group("author") or "").strip() or None
            identifier = work_id(title)
            works.setdefault(
                identifier,
                Work(
                    work_id=identifier,
                    source_work_id=None,
                    title=title,
                    title_normalized=title_key(title),
                    aliases=[],
                    author_name=author,
                    author_entity_id=None,
                    status="stub",
                ),
            )
            anchor = _anchor(book, block.block_id, match.start("title"), match.end("title"))
            relations.append(relation("same_topic_as", this.work_id, identifier, [anchor], "editor_text"))
            edited.append(identifier)
        if named := _NAMED_EDITION.search(block.text):
            title = named.group("title")
            identifier = work_id(title)
            works.setdefault(
                identifier,
                Work(
                    work_id=identifier,
                    source_work_id=None,
                    title=title,
                    title_normalized=title_key(title),
                    aliases=[],
                    author_name=book.metadata.editor,
                    author_entity_id=None,
                    status="stub",
                ),
            )
            anchor = _anchor(book, block.block_id, named.start("title"), named.end("title"))
            relations += [
                relation("tahqiq_of", identifier, target, [anchor], "editor_text") for target in edited
            ]

    for work in list(works.values()):
        if found := title_relation(work.title):
            type_, base = found
            base_id = work_id(base)
            works.setdefault(
                base_id,
                Work(
                    work_id=base_id,
                    source_work_id=None,
                    title=base,
                    title_normalized=title_key(base),
                    aliases=[],
                    author_name=None,
                    author_entity_id=None,
                    status="stub",
                ),
            )
            evidence = cited.get(work.work_id, [])[:1]
            if evidence:
                relations.append(
                    relation(type_, work.work_id, base_id, evidence, "editor_footnote", "inferred")
                )

    return RelatedWorks(
        sorted(works.values(), key=lambda w: w.work_id), sorted(relations, key=lambda r: r.relation_id)
    )
