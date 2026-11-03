# 03 — Data Contracts

These are the exact schemas that every module reads and writes. Names follow [DECISIONS.md](DECISIONS.md). The examples use **real values from the sample**, and each one was verified with Python against `data/demo_book_daraqutni.json`.

- Canonical schema version: `"1.0"` (ADR-002).
- Enrichment schema version: `"1.0"`.
- Offsets are code-point indices into the original block text, with `end` exclusive (ADR-003).
- Code lives in `src/ilm_engine/canonical/models.py` (canonical) and `src/ilm_engine/enrichment/models.py` (enrichment).

Contents:
1. [Common types](#1-common-types)
2. [Canonical book (adapter output)](#2-canonical-book-adapter-output)
3. [Anchor](#3-anchor)
4. [Issue](#4-issue)
5. [Document report](#5-document-report)
6. [Section and origin](#6-section-and-origin)
7. [Metadata with provenance](#7-metadata-with-provenance)
8. [Annotation](#8-annotation)
9. [Citation and internal reference](#9-citation-and-internal-reference)
10. [Work and work relation](#10-work-and-work-relation)
11. [Fact and knowledge unit](#11-fact-and-knowledge-unit)
12. [Genre schema summaries](#12-genre-schema-summaries)
13. [Entity](#13-entity)
14. [Relationship](#14-relationship)
15. [Validation result](#15-validation-result)
16. [Review item and decision](#16-review-item-and-decision)
17. [Run manifest](#17-run-manifest)
18. [Consolidated enrichment.json](#18-consolidated-enrichmentjson)
19. [SQLite DDL (MVP)](#19-sqlite-ddl-mvp)
20. [PostgreSQL DDL sketch (production)](#20-postgresql-ddl-sketch-production)
21. [JSON Schema export](#21-json-schema-export)

---

## 1. Common types

```python
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

BlockKind = Literal["text", "heading", "toc_heading", "footnote"]
Origin = Literal["author_text", "transmission_isnad", "editor_text", "editor_footnote", "ai_generated"]
Assertion = Literal["stated", "inferred"]
Genre = Literal["fiqh", "hadith", "tafsir", "seerah", "aqeedah", "history", "biography"]
ReviewStatus = Literal["auto_approved", "pending_review", "approved", "rejected", "edited", "reprocess_requested"]
Severity = Literal["info", "warning", "error"]
SensitiveCategory = Literal["prophetic_attribution", "hadith_grading", "fiqh_ruling",
                            "aqeedah_proposition", "narrator_disambiguation"]
ExtractionMethod = Literal["structural", "rule", "nlp", "llm", "llm_consensus", "human"]

IssueCode = Literal[
    "unknown_schema_version", "page_count_mismatch", "missing_page", "toc_without_block",
    "toc_page_offset", "heading_without_toc", "unlinked_footnote", "nested_footnote",
    "continued_footnote_joined", "broken_ref", "numbering_gap", "numbering_duplicate",
    "entry_without_footnote", "title_variant", "metadata_conflict", "evidence_not_found",
    "schema_invalid", "model_disagreement", "ambiguous_entity", "needs_llm",
    "sensitive_content", "unresolved_internal_ref", "anchor_stale", "source_hash_unverified",
]

PersonRelType = Literal["child_of", "parent_of", "sibling_of", "spouse_of", "mother_is",
                        "teacher_of", "student_of", "narrated_from"]
WorkRelType = Literal["sharh_of", "hashiyah_of", "mukhtasar_of", "translation_of",
                      "edition_of", "tahqiq_of", "cites", "same_topic_as"]
SiblingKind = Literal["full", "paternal", "maternal", "unknown"]

class Provenance(Strict):
    """How a value was produced. Attached to every derived record."""
    method: ExtractionMethod
    step: str                       # pipeline step name (DECISIONS §12b), e.g. "units"
    step_version: str               # e.g. "1.0.0"
    model_id: str | None = None     # e.g. "claude-sonnet-5-5"
    prompt_id: str | None = None    # e.g. "extract_biography"
    prompt_version: str | None = None  # e.g. "v1"
```

---

## 2. Canonical book (adapter output)

Produced by `ShamelaV3Adapter` (`source_code="src-shamela"`, `schema_version="3.0"`, `adapter_version="1.0.0"`).

```python
class SourceInfo(Strict):
    source_code: str            # "src-shamela"
    source_book_key: str        # "26"
    schema_version: str         # "3.0"   (source content schema)
    source_adapter_semver: str | None  # "1.3.0" (source system's own adapter; informational)
    adapter_id: str             # "shamela_v3"
    adapter_version: str        # "1.0.0" (our adapter)
    claim_type: str | None      # "faithful_to_source"
    source_declared_hash: str | None   # "1f974ece…" (content_sha256 as declared)
    source_declared_hash_verified: bool = False

class BookRef(Strict):
    pub_id: str                 # "pub_01M0CJECV4ZHFTP02BJQ6D3STJ"
    revision: int               # 6
    pub_ref: str                # "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6"
    source_work_id: str | None  # "wrk_01M0CJEXJ1ZJM9AEM1GYTHTYZE"
    edition_id: str | None      # "edt_01M49AFMMYHV5DGF9B2CQQBVBB"

class Span(Strict):
    cls: str = Field(alias="class")   # raw source class: "c1" | "c2" | "c4" | "c5" | ...
    start: int
    end: int
    text: str
    meaning: Literal["footnote_marker", "emphasis", "prophetic_speech",
                     "editor_bracket_heading", "unknown"] = "unknown"   # inferred mapping

class Ref(Strict):
    start: int
    end: int
    to: str                     # target block_id

class Block(Strict):
    block_id: str               # "b000135" (source id, never renumbered)
    order: int                  # global 0-based reading order
    page: int                   # printed page n
    volume: int
    kind: BlockKind
    text: str                   # ORIGINAL text, never modified
    marker: str | None = None   # footnote marker as in source, e.g. "٨ -", "١", "أ"
    continues: bool = False     # footnote continued from previous page
    refs: list[Ref] = []
    spans: list[Span] = []
    block_hash: str             # "sha256:<hex>" of text (ADR-017)
    raw_extras: dict[str, Any] = {}

class Page(Strict):
    volume: int
    n: int                      # printed page number
    scan_page: int              # PDF page number
    source_key: str             # Shamela page key (TOC source_page aligns to this!)
    source_url: str | None
    block_ids: list[str]
    raw_extras: dict[str, Any] = {}

class TocEntry(Strict):
    index: int
    title: str
    source_page_key: str        # raw "source_page" value = Page.source_key
    depth: int

class SourceMetadata(Strict):
    """Bibliographic data exactly as the source states it (not yet validated)."""
    title_as_source: str | None
    author_as_source: str | None
    author_name: str | None
    author_death_hijri: int | None
    editor: str | None
    publisher: str | None
    edition: str | None
    year_hijri: int | None
    year_gregorian: int | None
    category_id: str | None
    category_name: str | None
    claimed_page_count: int | None      # card "عدد الصفحات" (٧٢ → 72)
    page_numbering: str | None          # "matches_print"
    card: list[dict[str, str]] = []     # raw card rows {label, value, group}
    toc: list[TocEntry] = []

class SourceQuality(Strict):
    status: str | None          # "imperfect"
    passed: bool | None         # True
    claimed_pages: int | None   # 72
    held_pages: int | None      # 68
    short_pct: float | None     # 5.5555
    tolerance: str | None       # "5%"
    archive_code: str | None    # "E-VAL-SHORT"

class CanonicalBook(Strict):
    canonical_schema_version: Literal["1.0"] = "1.0"
    book: BookRef
    source: SourceInfo
    metadata: SourceMetadata
    quality: SourceQuality | None
    scan: dict[str, Any]        # {"available": true, "volumes": [1], "file": "demo_book_daraqutni_v1.pdf", "page_count": 80}
    pages: list[Page]
    blocks: dict[str, Block]    # keyed by block_id, insertion order = reading order
    raw_extras: dict[str, Any] = {}   # e.g. "timeline", "editions", "_meta" fields not mapped
    canonical_content_hash: str       # sha256 over all blocks (ADR-017)
```

**Mapping notes for `ShamelaV3Adapter`:**

| Source path | Canonical field |
|---|---|
| `pub.id`, `revision.r` | `book.pub_id`, `book.revision` |
| `content.pages[].n / scan_page / source_ref.key / source_ref.url` | `Page.n / scan_page / source_key / source_url` |
| `content.pages[].blocks[].b / kind / text / marker / continues / refs / spans` | `Block.*` |
| `metadata.source_attributes.toc[]` | `SourceMetadata.toc[]` (`source_page` → `source_page_key`) |
| `metadata.source_attributes.card[]` | `SourceMetadata.card` + parsed fields |
| `quality.auto.detail` | `SourceQuality` |
| `timeline`, `editions`, `_meta.*` not mapped | `CanonicalBook.raw_extras` |

**Example (one block, real):**

```json
{
  "block_id": "b000135", "order": 134, "page": 25, "volume": 1, "kind": "text",
  "text": "٨ - هند بنت عتيق بن عابد (١) بن عبد اللَّه بن عمر بن مخزوم؛ أسلمت (٢) وتزوجت، ولم يُروَ عنها شيءٌ (٣).",
  "marker": null, "continues": false,
  "refs": [{"start": 0, "end": 3, "to": "b000139"}, {"start": 25, "end": 28, "to": "b000140"},
           {"start": 66, "end": 69, "to": "b000141"}, {"start": 98, "end": 101, "to": "b000142"}],
  "spans": [{"class": "c2", "start": 25, "end": 28, "text": "(١)", "meaning": "footnote_marker"},
            {"class": "c2", "start": 66, "end": 69, "text": "(٢)", "meaning": "footnote_marker"},
            {"class": "c2", "start": 98, "end": 101, "text": "(٣)", "meaning": "footnote_marker"}],
  "block_hash": "sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989",
  "raw_extras": {}
}
```

**Example (page, real):** `{"volume": 1, "n": 25, "scan_page": 25, "source_key": "21", "source_url": "https://shamela.ws/book/26/21", "block_ids": ["b000134", "b000135", "…"]}`

Span meaning mapping (inferred, configurable in `config/default.yaml`): `c2` → `footnote_marker` (230), `c5` → `emphasis` (64), `c1` → `prophetic_speech` (8; e.g. `b000131` 31–66 "إنَّ له مرضعًا يتم رضاعة في الجنة"), `c4` → `editor_bracket_heading` (2; `b000421`, `b000586`).

---

## 3. Anchor

```python
class Anchor(Strict):
    pub_ref: str
    page: int
    scan_page: int
    block_id: str
    start: int
    end: int
    quote: str
    quote_truncated: bool = False
    block_hash: str
    status: Literal["valid", "stale", "orphaned"] = "valid"
    bbox: list[float] | None = None     # reserved for OCR sources; unused in MVP

    # invariant (validated in validation/evidence.py): block.text[start:end] == quote (unless quote_truncated)
```

```json
{"pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6", "page": 25, "scan_page": 25, "block_id": "b000135",
 "start": 78, "end": 97, "quote": "ولم يُروَ عنها شيءٌ",
 "block_hash": "sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989", "status": "valid"}
```

---

## 4. Issue

```python
class Issue(Strict):
    issue_id: str               # "iss_<12hex>"
    code: IssueCode
    severity: Severity
    target_kind: Literal["book", "page", "block", "section", "annotation", "citation",
                         "unit", "fact", "entity", "relationship", "metadata_field", "work"]
    target_id: str
    message: str
    anchors: list[Anchor] = []
    details: dict[str, Any] = {}
    provenance: Provenance
```

```json
{"issue_id": "iss_3f1c…", "code": "page_count_mismatch", "severity": "info",
 "target_kind": "book", "target_id": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6",
 "message": "Source claims 72 pages, 68 held. Missing printed pages 1, 2, 4, 18 are non-content (cover, publisher page, basmala, blank) per PDF check.",
 "details": {"claimed": 72, "held": 68, "missing_pages": [1, 2, 4, 18], "source_passed": true, "short_pct": 5.56, "tolerance_pct": 5},
 "provenance": {"method": "rule", "step": "document_analysis", "step_version": "1.0.0"}}
```

```json
{"issue_id": "iss_8a20…", "code": "nested_footnote", "severity": "warning",
 "target_kind": "annotation", "target_id": "b000215",
 "message": "Footnote with marker 'أ' has no incoming ref; matched to '(أ)' inside footnote b000210 [30:33].",
 "details": {"parent_footnote": "b000210", "parent_start": 30, "parent_end": 33},
 "provenance": {"method": "rule", "step": "annotations", "step_version": "1.0.0"}}
```

---

## 5. Document report

```python
class DocumentReport(Strict):
    pub_ref: str
    page_count_held: int                # 68
    page_count_claimed: int | None      # 72
    printed_page_range: tuple[int, int] # (3, 72)
    missing_printed_pages: list[int]    # [1, 2, 4, 18]
    pdf_page_count: int | None          # 80
    pdf_pages_not_in_json: list[int]    # [1, 2, 4, 18, 73, 74, 75, 76, 77, 78, 79, 80]
    block_counts: dict[str, int]        # {"text": 260, "footnote": 317, "heading": 15, "toc_heading": 2}
    block_total: int                    # 594
    ref_count: int                      # 300
    refs_from_footnotes: int            # 0
    continued_footnotes: int            # 16
    span_class_counts: dict[str, int]   # {"c2": 230, "c5": 64, "c1": 8, "c4": 2}
    empty_blocks: list[str]
    duplicate_blocks: list[list[str]]
    source_quality: SourceQuality | None
    issues: list[str]                   # issue_ids
```

---

## 6. Section and origin

```python
class Section(Strict):
    section_id: str             # "sec_<12hex>"
    title: str                  # original heading text
    level: int                  # 1 or 2 (TOC depth); 0 = book root
    heading_block_id: str | None
    toc_index: int | None
    toc_source_page_key: str | None
    start_block_id: str
    end_block_id: str           # inclusive
    start_page: int
    end_page: int
    parent_id: str | None
    children: list[str] = []
    origin: Origin              # dominant origin of the section's body
    provenance: Provenance

class OriginSpan(Strict):
    """Contiguous run of blocks sharing an origin (origin_map.json)."""
    origin: Origin
    start_block_id: str
    end_block_id: str
    start_page: int
    end_page: int
    rule: str                   # e.g. "footnote_kind", "before_author_intro", "isnad_formula", "override"
    block_count: int
```

**Example (real):**

```json
{"section_id": "sec_…", "title": "* وأخوة أولاد رسول اللَّه -صلى الله عليه وسلم- من أُمهم خديجة:",
 "level": 1, "heading_block_id": "b000134", "toc_index": 8, "toc_source_page_key": "21",
 "start_block_id": "b000134", "end_block_id": "…", "start_page": 25, "end_page": 33,
 "parent_id": "sec_root…", "origin": "author_text",
 "provenance": {"method": "structural", "step": "structure", "step_version": "1.0.0"}}
```

Note: TOC entry 8 has `source_page: "21"`, which is the Shamela key of printed page 25. It is aligned through `Page.source_key`, not through `n`.

```json
[
 {"origin": "editor_text", "start_block_id": "b000012", "end_block_id": "b000080", "start_page": 5, "end_page": 16, "rule": "before_author_intro", "block_count": 0},
 {"origin": "transmission_isnad", "start_block_id": "b000081", "end_block_id": "…", "start_page": 17, "end_page": 17, "rule": "manuscript_title_page", "block_count": 0},
 {"origin": "transmission_isnad", "start_block_id": "b000093", "end_block_id": "b000093", "start_page": 19, "end_page": 19, "rule": "isnad_formula", "block_count": 1},
 {"origin": "author_text", "start_block_id": "b000098", "end_block_id": "…", "start_page": 20, "end_page": 72, "rule": "author_section", "block_count": 0}
]
```
(`block_count` and the `…` boundaries are computed at runtime. The pages and boundary blocks shown are verified.)

---

## 7. Metadata with provenance

```python
class MetadataSource(Strict):
    kind: Literal["existing_metadata", "book_content", "pdf_visual", "external_catalog"]
    path: str | None = None     # e.g. "metadata.source_attributes.editor"
    anchors: list[Anchor] = []

class MetadataField(Strict):
    value: Any
    normalized: Any | None = None
    sources: list[MetadataSource]
    assertion: Assertion
    origin: Origin               # whose statement the value is
    confidence: float
    conflicts: list[dict[str, Any]] = []   # [{value, source}] when sources disagree
    review_status: ReviewStatus

class BookMetadata(Strict):
    pub_ref: str
    title: MetadataField
    title_variants: list[str]
    author: MetadataField             # value: {"name": ..., "kunya": "أبو الحسن", "death_hijri": 385}
    editor: MetadataField
    publisher: MetadataField
    edition: MetadataField
    year_hijri: MetadataField
    year_gregorian: MetadataField
    volumes: MetadataField
    language: MetadataField
    category: MetadataField
    genre_primary: MetadataField      # filled by step "genre"
    genre_secondary: list[MetadataField]
    missing_fields: list[str]
    issues: list[str]
```

**Example (real): author death year confirmed by content.**

```json
{"value": {"name": "أبو الحسن علي بن عمر بن أحمد الدارقطني", "death_hijri": 385},
 "sources": [
   {"kind": "existing_metadata", "path": "metadata.source_attributes.author.death.hijri"},
   {"kind": "book_content", "anchors": [{"pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6", "page": 9, "scan_page": 9,
     "block_id": "b000049", "start": 24, "end": 51, "quote": "سنةٍ خمسٍ وثمانين وثلاث مئة",
     "block_hash": "sha256:b4f1f176241242ffbd6fa49106557dc458dd6be7240bbbf54855ba3c6edd9292"}]}],
 "assertion": "stated", "origin": "editor_text", "confidence": 0.95, "conflicts": [], "review_status": "auto_approved"}
```

Title variants detected: `"الإخوة والأخوات"` (card) and `"الأُخوة والأَخوات"` (`b000001`). They are equal after normalization, so the issue `title_variant` is `info`.

---

## 8. Annotation

```python
class Annotation(Strict):
    annotation_id: str          # "ann_<12hex>"
    type: Literal["footnote", "endnote", "sidenote", "nested_footnote"]
    source_block_id: str        # block containing the marker
    marker_anchor: Anchor       # the marker span, e.g. "(١)" or "٨ -"
    target_block_ids: list[str] # footnote block(s); continued parts joined in order
    marker_text: str | None     # target footnote marker as in source
    link_method: Literal["source_ref", "marker_match", "llm_candidate"]
    is_entry_note: bool         # marker like "N -" → biographical note of entry N
    status: Literal["verified", "candidate", "unlinked"]
    origin: Origin = "editor_footnote"
    provenance: Provenance
```

**Example (real): entry-level note.**

```json
{"annotation_id": "ann_…", "type": "footnote", "source_block_id": "b000105",
 "marker_anchor": {"pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6", "page": 21, "scan_page": 21, "block_id": "b000105",
   "start": 0, "end": 3, "quote": "١ -", "block_hash": "sha256:550b74804d674fdf53843216ac6c007ac5fd4106089d62a3f4fd03aef6e5f464"},
 "target_block_ids": ["b000109"], "marker_text": "١ -", "link_method": "source_ref",
 "is_entry_note": true, "status": "verified", "origin": "editor_footnote",
 "provenance": {"method": "structural", "step": "annotations", "step_version": "1.0.0"}}
```

Continued footnote (real): `b000097` (p. 19, ends with "=") plus `b000103` (p. 20, `continues: true`) gives `target_block_ids: ["b000097", "b000103"]` and issue `continued_footnote_joined` (info).
Nested footnote (real): `b000215` (marker "أ") gets `type: "nested_footnote"`, `source_block_id: "b000210"`, a marker anchor at 30–33 "(أ)", and `link_method: "marker_match"`.

---

## 9. Citation and internal reference

```python
class Locator(Strict):
    raw: str                    # "(٨/ ١٥٧)"
    volume: int | None          # 8
    page: int | None            # 157
    number: int | None = None   # for "(رقم: ١٣٨٢)"
    page_label: str | None = None  # for "(ص: ١٣٣)"

class Citation(Strict):
    citation_id: str            # "cit_<12hex>"
    title_raw: str              # "الإصابة"
    title_normalized: str       # "الاصابه"
    work_id: str | None         # resolved Work ("wrk_<12hex>") or None
    author_hint: str | None     # e.g. "للمصنّف", "لابن ماكولا"
    locators: list[Locator]
    anchor: Anchor              # on the title
    context: Literal["footnote", "body"]
    origin: Origin
    resolution: Literal["alias_table", "agent", "unresolved"]
    confidence: float
    provenance: Provenance

class InternalRef(Strict):
    internal_ref_id: str        # "ann_<12hex>" family; prefix "ann"
    kind: Literal["entry_number", "forward", "backward"]
    anchor: Anchor
    target_unit_id: str | None  # ku_… of the referenced entry
    target_entry_no: int | None
    status: Literal["resolved", "unresolved"]
    provenance: Provenance
```

**Example (real):**

```json
{"citation_id": "cit_…", "title_raw": "الإصابة", "title_normalized": "الاصابه", "work_id": "wrk_…",
 "author_hint": null, "locators": [{"raw": "(٨/ ١٥٧)", "volume": 8, "page": 157}],
 "anchor": {"pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6", "page": 25, "scan_page": 25, "block_id": "b000139",
   "start": 15, "end": 22, "quote": "الإصابة", "block_hash": "sha256:9fda7aa4d1e3aba8065143bd49c5d867dc72a70553d92847e3ac7281c98b210c"},
 "context": "footnote", "origin": "editor_footnote", "resolution": "alias_table", "confidence": 0.95,
 "provenance": {"method": "rule", "step": "citations", "step_version": "1.0.0"}}
```

```json
{"internal_ref_id": "ann_…", "kind": "entry_number",
 "anchor": {"pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6", "page": 11, "scan_page": 11, "block_id": "b000063",
   "start": 60, "end": 74, "quote": "ترجمة رقم (٣٣)", "block_hash": "sha256:acd06774b536028f9d5332088cf11f675928901f8219beb3f5e7801042b0c88f"},
 "target_unit_id": "ku_…", "target_entry_no": 33, "status": "resolved",
 "provenance": {"method": "rule", "step": "citations", "step_version": "1.0.0"}}
```

---

## 10. Work and work relation

```python
class Work(Strict):
    work_id: str                # "wrk_<12hex>" (ours) — distinct from source ids (26 uppercase chars)
    source_work_id: str | None  # "wrk_01M0CJEXJ1ZJM9AEM1GYTHTYZE" for the sample book itself
    title: str
    title_normalized: str
    aliases: list[str]
    author_name: str | None
    author_entity_id: str | None
    status: Literal["catalog", "stub", "this_book"]

class WorkRelation(Strict):
    relation_id: str            # "rel_<12hex>"
    type: WorkRelType
    subject_work_id: str
    object_work_id: str
    evidence: list[Anchor]
    origin: Origin
    assertion: Assertion
    confidence: float
    count: int = 1              # for "cites": number of citations aggregated
    review_status: ReviewStatus
    provenance: Provenance
```

**Example (real): same-topic work named by the editor.**

```json
{"relation_id": "rel_…", "type": "same_topic_as", "subject_work_id": "wrk_<this book>", "object_work_id": "wrk_<الأخوة لأبي داود>",
 "evidence": [{"pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6", "page": 5, "scan_page": 5, "block_id": "b000018",
   "start": 151, "end": 182, "quote": "الأُخوة الذين رُويَ عنهم الحديث",
   "block_hash": "sha256:f754be0c66ec6ad84cea5dc647341f637ab61672d092d2ea4ee2a791de7eb437"}],
 "origin": "editor_text", "assertion": "stated", "confidence": 0.9, "count": 1, "review_status": "auto_approved",
 "provenance": {"method": "rule", "step": "related_works", "step_version": "1.0.0"}}
```

Other real evidence in `b000018`: "تسمية من رُويَ عنه من أولاد العشرة" (216–250) and "الرّواة من الأُخوة والأخوات" (362–389).

---

## 11. Fact and knowledge unit

```python
class Fact(Strict):
    fact_id: str                # "ku_<12hex>#f<N>" (child of unit)
    predicate: str              # controlled per genre, e.g. "converted_to_islam", "married", "has_narration", "married_to", "marriage_year_hijri"
    object: Any                 # literal value or entity_id
    object_entity_id: str | None = None
    evidence: list[Anchor]      # ≥1, verified (ADR-007)
    origin: Origin
    assertion: Assertion
    confidence: float
    sensitive: list[SensitiveCategory] = []
    review_status: ReviewStatus
    provenance: Provenance

class KnowledgeUnit(Strict):
    unit_id: str                # "ku_<12hex>"
    genre: Genre
    sub_type: str | None        # "ansab"
    unit_type: str              # "biographical_entry", "hadith", "masala", ...
    entry_no: int | None        # 8
    section_id: str
    anchors: list[Anchor]       # the unit's own text span(s)
    note_annotation_ids: list[str]  # entry-level footnotes etc.
    subject_entity_id: str | None
    payload: dict[str, Any]     # genre-schema object (validated by the genre plugin)
    facts: list[Fact]
    origin: Origin
    confidence: float
    review_status: ReviewStatus
    issues: list[str]
    provenance: Provenance
```

**Example (real): entry 8.**

```json
{
  "unit_id": "ku_…", "genre": "biography", "sub_type": "ansab", "unit_type": "biographical_entry",
  "entry_no": 8, "section_id": "sec_<b000134>",
  "anchors": [{"pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6", "page": 25, "scan_page": 25, "block_id": "b000135",
               "start": 0, "end": 102, "quote": "٨ - هند بنت عتيق بن عابد (١) بن عبد اللَّه بن عمر بن مخزوم؛ أسلمت (٢) وتزوجت، ولم يُروَ عنها شيءٌ (٣).",
               "block_hash": "sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989"}],
  "note_annotation_ids": ["ann_<b000135:0:b000139>"],
  "subject_entity_id": "ent_<hind bint atiq>",
  "payload": {"person_surface": "هند بنت عتيق بن عابد", "person_span": [4, 24], "gender": "f",
              "nasab": ["عتيق", "عابد", "عبد اللَّه", "عمر", "مخزوم"]},
  "facts": [
    {"fact_id": "ku_…#f1", "predicate": "converted_to_islam", "object": true,
     "evidence": [{"pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6", "page": 25, "scan_page": 25, "block_id": "b000135",
                   "start": 60, "end": 65, "quote": "أسلمت", "block_hash": "sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989"}],
     "origin": "author_text", "assertion": "stated", "confidence": 0.9, "sensitive": [], "review_status": "auto_approved",
     "provenance": {"method": "llm_consensus", "step": "units", "step_version": "1.0.0", "model_id": "claude-sonnet-5-5", "prompt_id": "extract_biography", "prompt_version": "v1"}},
    {"fact_id": "ku_…#f2", "predicate": "married", "object": true,
     "evidence": [{"…": "…", "block_id": "b000135", "start": 70, "end": 76, "quote": "وتزوجت"}],
     "origin": "author_text", "assertion": "stated", "confidence": 0.9, "review_status": "auto_approved", "provenance": {"…": "…"}},
    {"fact_id": "ku_…#f3", "predicate": "has_narration", "object": false,
     "evidence": [{"…": "…", "block_id": "b000135", "start": 78, "end": 97, "quote": "ولم يُروَ عنها شيءٌ"}],
     "origin": "author_text", "assertion": "stated", "confidence": 0.9, "review_status": "auto_approved", "provenance": {"…": "…"}}
  ],
  "origin": "author_text", "confidence": 0.9, "review_status": "auto_approved", "issues": [],
  "provenance": {"method": "rule", "step": "units", "step_version": "1.0.0"}
}
```

**Example (real): an editor-footnote fact, which is not the author's statement.** From `b000109` (note on entry 1 فاطمة, `b000105`):
`{"predicate": "married_to", "object": "علي", "evidence": [{"block_id": "b000109", "start": 37, "end": 77, "quote": "تزوجها عليّ في السَّنة الثانية من الهجرة"}], "origin": "editor_footnote", "assertion": "stated"}`

**Example (real): an inferred fact.** "Fatimah is a child of the Prophet ﷺ" has evidence heading `b000104` (0–40) plus `b000105` (4–9 "فاطمة"), `origin: "ai_generated"`, `assertion: "inferred"`.

**Entry detection rule:** regex `(?<![٠-٩(/])([٠-٩]+) ?- ` on `author_text` blocks from page 21. This gives 75 entries, numbered 1–75. Entry #32 is mid-sentence: `b000294` "٣١ - وأُمية. … وأختهم: ٣٢ - أروى؛ …" (offsets 23–32 "٣٢ - أروى"). Entry #32 has no entry-level footnote (issue `entry_without_footnote`, info).

---

## 12. Genre schema summaries

These are field lists only. The full plugin detail is in `06-ai-strategy.md` (ADR-013). Every genre unit also has the common `KnowledgeUnit` fields above. `(S)` marks a sensitive field (ADR-009).

| Genre | `unit_type` | Payload fields |
|---|---|---|
| `fiqh` | `masala` | `question`, `hukm` (S), `dalil[]` {type: quran/hadith/ijma/qiyas, text_anchor}, `madhhab`, `qail` (scholar entity), `khilaf[]` {madhhab, opinion, qail}, `conditions[]` |
| `hadith` | `hadith` / `takhrij` | `matn`, `isnad[]` {narrator_entity_id, transmission_term: حدثنا/أخبرنا/عن}, `rawi_a3la`, `takhrij[]` {collection, book, volume, page, number}, `grading` (S) {term: sahih/hasan/daif/…, grader}, `sharh_ref`, `prophetic_attribution` (S) |
| `tafsir` | `tafsir_unit` | `ayah_ref` {surah, ayah_from, ayah_to}, `ayah_text_anchor`, `explanation`, `qawl[]` {mufassir_entity_id, opinion}, `method` (bi'l-ma'thur/bi'l-ra'y), `linguistic_notes[]` |
| `seerah` | `event` | `event_name`, `date` {hijri_year, month, day, precision}, `place`, `persons[]` {entity_id, role}, `sequence_hint` |
| `aqeedah` | `proposition` | `concept`, `proposition` (S), `evidence[]` {type, anchor}, `school` (Athari/Ash'ari/Maturidi/…), `refuted_view` |
| `history` | `event` | `event_name`, `date`, `chronology_order`, `place`, `persons[]`, `dynasty`, `source_claim` |
| `biography` (incl. `ansab`) | `biographical_entry` | `person_surface`, `person_span`, `ism`, `kunya`, `laqab`, `nisba[]`, `nasab[]`, `gender`, `birth` {year_hijri, place}, `death` {year_hijri, place}, `teachers[]`, `students[]`, `relatives[]` {relation, entity_id, kind}, `companion_status` (sahabi/not), `narration_status` (has_narration bool) |

---

## 13. Entity

```python
class PersonName(Strict):
    ism: str | None             # "هند"
    kunya: str | None           # "أبو الحسن"
    laqab: str | None
    nisba: list[str] = []       # ["البغدادي"]
    nasab: list[str] = []       # ancestors in order: ["عتيق", "عابد", "عبد اللَّه", "عمر", "مخزوم"]
    full_surface: str

class Entity(Strict):
    entity_id: str              # "ent_<12hex>"
    entity_type: Literal["person", "place", "work", "event", "concept", "group"]
    canonical_name: str
    canonical_name_normalized: str
    name: PersonName | None     # for persons
    gender: Literal["m", "f", "unknown"] = "unknown"
    aliases: list[str] = []
    roles: list[Literal["author", "editor", "narrator", "sahabi", "scholar", "subject"]] = []
    mentions: list[Anchor]
    external_ids: dict[str, str] = {}   # e.g. {"shamela_author": "223"}
    disambiguation: Literal["unique", "resolved", "ambiguous"] = "unique"
    candidates: list[str] = []          # other entity_ids when ambiguous
    confidence: float
    review_status: ReviewStatus
    provenance: Provenance
```

**Examples (real):**

```json
[
 {"entity_id": "ent_…", "entity_type": "person", "canonical_name": "هند بنت عتيق بن عابد",
  "name": {"ism": "هند", "kunya": null, "laqab": null, "nisba": [], "nasab": ["عتيق", "عابد", "عبد اللَّه", "عمر", "مخزوم"], "full_surface": "هند بنت عتيق بن عابد"},
  "gender": "f", "roles": ["subject"], "mentions": [{"block_id": "b000135", "start": 4, "end": 24, "quote": "هند بنت عتيق بن عابد", "…": "…"}],
  "disambiguation": "unique", "confidence": 0.9, "review_status": "auto_approved", "provenance": {"…": "…"}},
 {"entity_id": "ent_…", "entity_type": "person", "canonical_name": "هند بن أبي هالة",
  "name": {"ism": "هند", "nasab": ["أبي هالة"], "full_surface": "هند"}, "gender": "m",
  "mentions": [{"block_id": "b000136", "start": 4, "end": 8, "quote": "وهند", "…": "…"}],
  "disambiguation": "resolved", "confidence": 0.9, "review_status": "auto_approved", "provenance": {"method": "llm_consensus", "…": "…"}},
 {"entity_id": "ent_…", "entity_type": "person", "canonical_name": "علي بن عمر الدارقطني",
  "name": {"ism": "علي", "kunya": "أبو الحسن", "nisba": ["الدارقطني"], "nasab": ["عمر", "أحمد"], "full_surface": "أبو الحسن علي بن عمر بن أحمد الدارقطني"},
  "gender": "m", "aliases": ["الدارقطني", "الدَّارقطني", "أبو الحسن علي بن عمر بن أحمد بن مهدي"], "roles": ["author"],
  "external_ids": {"shamela_author": "223"}, "mentions": ["…"], "confidence": 0.95, "review_status": "auto_approved", "provenance": {"…": "…"}}
]
```

Note: entry 9 (`b000136`, "وهند") is **male**. "ابنا" in `b000137` is a dual masculine noun covering entries 9 and 10 ("ابنا أبي هالة", offsets 12–25). A model that copies the gender of entry 8 (Hind bint Atiq, female) is wrong.

---

## 14. Relationship

```python
class RelationshipAttrs(Strict):
    kind: SiblingKind | None = None          # for sibling_of
    via_parent_entity_id: str | None = None  # shared parent
    group_id: str | None = None              # sibling group (closure phrase)
    mother_status: Literal["umm_walad", "named", "unknown"] | None = None

class Relationship(Strict):
    relation_id: str            # "rel_<12hex>"
    type: PersonRelType
    subject_entity_id: str
    object_entity_id: str
    attrs: RelationshipAttrs = RelationshipAttrs()
    evidence: list[Anchor]      # ≥1
    origin: Origin
    assertion: Assertion
    confidence: float
    sensitive: list[SensitiveCategory] = []
    review_status: ReviewStatus
    provenance: Provenance
```

**Examples (real): entries 9 and 10, sons of Abu Hala.**

```json
[
 {"relation_id": "rel_…", "type": "sibling_of", "subject_entity_id": "ent_<هند بن أبي هالة>", "object_entity_id": "ent_<هالة بن أبي هالة>",
  "attrs": {"kind": "full", "via_parent_entity_id": "ent_<أبو هالة مالك بن النباش>", "group_id": "grp_<b000137:12>"},
  "evidence": [{"block_id": "b000137", "start": 12, "end": 25, "quote": "ابنا أبي هالة", "…": "…"}],
  "origin": "author_text", "assertion": "stated", "confidence": 0.9, "review_status": "auto_approved", "provenance": {"method": "llm_consensus", "…": "…"}},
 {"relation_id": "rel_…", "type": "child_of", "subject_entity_id": "ent_<هالة بن أبي هالة>", "object_entity_id": "ent_<أبو هالة مالك بن النباش>",
  "evidence": [{"block_id": "b000137", "start": 12, "end": 25, "quote": "ابنا أبي هالة", "…": "…"}],
  "origin": "author_text", "assertion": "stated", "confidence": 0.9, "review_status": "auto_approved", "provenance": {"…": "…"}},
 {"relation_id": "rel_…", "type": "sibling_of", "subject_entity_id": "ent_<هند بنت عتيق>", "object_entity_id": "ent_<فاطمة>",
  "attrs": {"kind": "maternal"},
  "evidence": [{"block_id": "b000134", "start": 46, "end": 62, "quote": " من أُمهم خديجة:", "…": "…"}],
  "origin": "ai_generated", "assertion": "inferred", "confidence": 0.75, "review_status": "pending_review", "provenance": {"…": "…"}}
]
```

Rule: "لأم ولد" sets `attrs.mother_status = "umm_walad"` and is **not** `kind: maternal` (DECISIONS §11).

---

## 15. Validation result

```python
class ConfidenceFactors(Strict):
    base: float                 # 0.95 rule/structural | 0.75 llm
    evidence: float             # 1.0 | 0.9 | 0
    schema: float               # 1.0 | 0.9 | 0
    agreement: float            # 1.2 | 0.9 | 1.0
    penalties: dict[str, float] = {}   # {"ambiguous_entity": 0.8}

class ValidationResult(Strict):
    target_kind: str            # "fact" | "unit" | "entity" | "relationship" | "citation" | "metadata_field" | "annotation"
    target_id: str
    schema_valid: bool
    evidence_found: bool
    evidence_match: Literal["exact", "normalized", "none"]
    model_outputs: list[dict[str, Any]] = []   # [{"model_id": ..., "value": ...}]
    agreement: Literal["agree", "disagree", "judge_resolved", "single"] = "single"
    factors: ConfidenceFactors
    confidence: float           # clamp01(product)
    sensitive: list[SensitiveCategory] = []
    threshold: float            # applied threshold (default 0.80)
    decision: ReviewStatus      # auto_approved | pending_review
    issues: list[str] = []
```

```json
{"target_kind": "fact", "target_id": "ku_…#f1", "schema_valid": true, "evidence_found": true, "evidence_match": "exact",
 "model_outputs": [{"model_id": "claude-sonnet-5-5", "value": true}, {"model_id": "<verifier>", "value": true}],
 "agreement": "agree", "factors": {"base": 0.75, "evidence": 1.0, "schema": 1.0, "agreement": 1.2, "penalties": {}},
 "confidence": 0.9, "sensitive": [], "threshold": 0.8, "decision": "auto_approved", "issues": []}
```

---

## 16. Review item and decision

```python
class ReviewItem(Strict):
    review_id: str              # "rev_<12hex>"
    target_kind: str
    target_id: str
    reason: list[Literal["low_confidence", "sensitive", "discrepancy", "needs_llm", "structural_issue"]]
    sensitive: list[SensitiveCategory] = []
    required_role: Literal["editor_reviewer", "scholar_reviewer"]
    priority: int               # lower = earlier; sensitive=0, then by confidence, then by dependents
    confidence: float | None
    proposed_value: Any
    model_outputs: list[dict[str, Any]] = []
    anchors: list[Anchor]
    context_block_ids: list[str]
    pdf: dict[str, Any]         # {"file": "demo_book_daraqutni_v1.pdf", "page": 35}
    issues: list[str]
    status: ReviewStatus = "pending_review"

class ReviewDecision(Strict):
    review_id: str
    decision: Literal["approved", "rejected", "edited", "reprocess_requested"]
    new_value: Any | None = None
    reviewer_id: str
    reviewer_role: Literal["editor_reviewer", "scholar_reviewer", "admin"]
    reason: str | None = None
    decided_at: str             # ISO 8601 (only in audit records, not in content files)
```

**Example (real): hadith grading in a footnote.**

```json
{"review_id": "rev_…", "target_kind": "unit", "target_id": "ku_<takhrij b000228>",
 "reason": ["sensitive"], "sensitive": ["hadith_grading"], "required_role": "scholar_reviewer", "priority": 0, "confidence": 0.9,
 "proposed_value": {"grading": {"term": "daif", "reason": "لكثرة المجاهيل"}, "takhrij": [{"collection": "الطبراني، الكبير", "volume": 3, "page": 166, "number": 3258}]},
 "anchors": [{"pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6", "page": 35, "scan_page": 35, "block_id": "b000228",
   "start": 115, "end": 142, "quote": "وإسناده ضعيف لكثرة المجاهيل",
   "block_hash": "sha256:13fb65ec7c5a52241bae650ed6dffd510c5ad6d6409f49f156bc78588325a0ce"}],
 "context_block_ids": ["b000228"], "pdf": {"file": "demo_book_daraqutni_v1.pdf", "page": 35},
 "issues": ["iss_<sensitive_content>"], "status": "pending_review"}
```

Training export (ADR-015): `output/<pub_ref>/training_examples.jsonl`. Each line is `{task, genre, input_block_ids, input_text, output, evidence, decision, reviewer_role, prompt_version, model_id}`.

---

## 17. Run manifest

```python
class FileHash(Strict):
    path: str
    sha256: str
    bytes: int

class StepRecord(Strict):
    name: str                   # one of DECISIONS §12b, in order
    version: str
    status: Literal["ran", "cached", "skipped", "failed"]
    cache_key: str
    duration_ms: int
    outputs: list[str]

class RunManifest(Strict):
    run_id: str                 # "run_<12hex>"
    pub_ref: str
    started_at: str
    finished_at: str
    code_version: str           # git sha or "dirty-<hash>"
    config_hash: str
    canonical_schema_version: str   # "1.0"
    enrichment_schema_version: str  # "1.0"
    normalizer_version: str         # e.g. "1.0.0"
    adapter: dict[str, str]         # {"id": "shamela_v3", "version": "1.0.0", "source_code": "src-shamela", "schema_version": "3.0"}
    llm: dict[str, Any]             # {"provider": "null", "routes": {...}, "models": [...], "prompts": {"extract_biography": "v1"}}
    steps: list[StepRecord]
    inputs: list[FileHash]
    outputs: list[FileHash]
    integrity: dict[str, Any]       # {"originals_unchanged": true, "anchors_checked": N, "stale": 0, "canonical_content_hash": "…", "source_declared_hash_verified": false}
    counts: dict[str, int]          # {"blocks": 594, "units": 75, "entities": ..., "review_items": ...}
```

Step names in order: `ingest`, `adapt`, `integrity_register`, `document_analysis`, `structure`, `origin`, `metadata`, `genre`, `annotations`, `citations`, `related_works`, `units`, `entities`, `relations`, `search_index`, `validate`, `review_queue`, `store`, `export`, `integrity_verify`, `manifest`.

---

## 18. Consolidated enrichment.json

```json
{
  "enrichment_schema_version": "1.0",
  "pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6",
  "run_id": "run_…",
  "source": {"source_code": "src-shamela", "schema_version": "3.0", "adapter": "shamela_v3@1.0.0",
             "canonical_content_hash": "…", "source_declared_hash": "1f974ece9429393b052de38052876b65ed195f83d3b6d55773691f2599f5c582",
             "source_declared_hash_verified": false},
  "document_report": {"…": "DocumentReport"},
  "metadata": {"…": "BookMetadata"},
  "structure": {"root_section_id": "sec_…", "sections": ["Section …"]},
  "origin_map": ["OriginSpan …"],
  "annotations": ["Annotation …"],
  "internal_refs": ["InternalRef …"],
  "citations": ["Citation …"],
  "works": ["Work …"],
  "work_relations": ["WorkRelation …"],
  "knowledge_units": ["KnowledgeUnit …"],
  "entities": ["Entity …"],
  "relationships": ["Relationship …"],
  "validation": ["ValidationResult …"],
  "issues": ["Issue …"],
  "review_queue_ids": ["rev_…"],
  "stats": {"blocks": 594, "pages": 68, "sections": 17, "units": 75, "annotations": 300, "citations": 0, "entities": 0, "relationships": 0, "review_items": 0}
}
```
(Stats `0` = computed at runtime. Sections ≥ 17 TOC entries, plus root and any heading without a TOC entry.)

The separate files in `output/<pub_ref>/` (DECISIONS §10) hold the same objects split by type. `enrichment.json` is their merge, sorted by ID.

---

## 19. SQLite DDL (MVP)

```sql
CREATE TABLE book (pub_ref TEXT PRIMARY KEY, pub_id TEXT NOT NULL, revision INTEGER NOT NULL,
  source_code TEXT, schema_version TEXT, adapter TEXT, canonical_content_hash TEXT NOT NULL,
  source_declared_hash TEXT, source_declared_hash_verified INTEGER DEFAULT 0);
CREATE TABLE block (block_id TEXT, pub_ref TEXT, ord INTEGER, page INTEGER, scan_page INTEGER,
  kind TEXT, origin TEXT, block_hash TEXT NOT NULL, PRIMARY KEY (pub_ref, block_id));  -- no text copy
CREATE TABLE section (section_id TEXT PRIMARY KEY, pub_ref TEXT, parent_id TEXT, level INTEGER,
  title TEXT, heading_block_id TEXT, start_block_id TEXT, end_block_id TEXT, origin TEXT, data JSON);
CREATE TABLE anchor (anchor_id TEXT PRIMARY KEY, owner_kind TEXT, owner_id TEXT, pub_ref TEXT,
  block_id TEXT, start INTEGER, "end" INTEGER, quote TEXT, block_hash TEXT, status TEXT DEFAULT 'valid');
CREATE INDEX anchor_owner ON anchor(owner_kind, owner_id);
CREATE INDEX anchor_block ON anchor(pub_ref, block_id);
CREATE TABLE annotation (annotation_id TEXT PRIMARY KEY, pub_ref TEXT, type TEXT, source_block_id TEXT,
  target_block_ids JSON, link_method TEXT, status TEXT, data JSON);
CREATE TABLE citation (citation_id TEXT PRIMARY KEY, pub_ref TEXT, title_normalized TEXT, work_id TEXT, data JSON);
CREATE TABLE work (work_id TEXT PRIMARY KEY, title TEXT, title_normalized TEXT, status TEXT, data JSON);
CREATE TABLE work_relation (relation_id TEXT PRIMARY KEY, type TEXT, subject_work_id TEXT, object_work_id TEXT,
  origin TEXT, assertion TEXT, confidence REAL, review_status TEXT, data JSON);
CREATE TABLE knowledge_unit (unit_id TEXT PRIMARY KEY, pub_ref TEXT, genre TEXT, unit_type TEXT, entry_no INTEGER,
  section_id TEXT, subject_entity_id TEXT, origin TEXT, confidence REAL, review_status TEXT, payload JSON);
CREATE TABLE fact (fact_id TEXT PRIMARY KEY, unit_id TEXT REFERENCES knowledge_unit, predicate TEXT, object JSON,
  origin TEXT, assertion TEXT, confidence REAL, sensitive JSON, review_status TEXT, provenance JSON);
CREATE TABLE entity (entity_id TEXT PRIMARY KEY, entity_type TEXT, canonical_name TEXT, canonical_name_normalized TEXT,
  gender TEXT, disambiguation TEXT, confidence REAL, review_status TEXT, data JSON);
CREATE TABLE relationship (relation_id TEXT PRIMARY KEY, type TEXT, subject_entity_id TEXT, object_entity_id TEXT,
  attrs JSON, origin TEXT, assertion TEXT, confidence REAL, review_status TEXT, provenance JSON);
CREATE TABLE issue (issue_id TEXT PRIMARY KEY, code TEXT, severity TEXT, target_kind TEXT, target_id TEXT, data JSON);
CREATE TABLE validation (target_kind TEXT, target_id TEXT, confidence REAL, decision TEXT, data JSON,
  PRIMARY KEY (target_kind, target_id));
CREATE TABLE review_item (review_id TEXT PRIMARY KEY, target_kind TEXT, target_id TEXT, priority INTEGER,
  required_role TEXT, status TEXT, data JSON);
CREATE TABLE review_audit (review_id TEXT, decided_at TEXT, reviewer_id TEXT, reviewer_role TEXT,
  decision TEXT, old_value JSON, new_value JSON, reason TEXT);
CREATE TABLE run (run_id TEXT PRIMARY KEY, pub_ref TEXT, manifest JSON);
```

The `block` table stores hashes, not text. Text is resolved from the read-only original through the anchor resolver (ADR-001).

---

## 20. PostgreSQL DDL sketch (production)

Same tables as SQLite, with these changes:
- `JSON` → `JSONB` with GIN indexes on `payload` and `data`.
- Partitioning by `pub_ref` hash for `anchor`, `fact` and `annotation`.
- `entity` gains `embedding vector(1024)` (pgvector, BGE-M3), until the move to Qdrant (ADR-005).
- An `outbox(event_id BIGSERIAL, table_name, row_id, op, payload JSONB, created_at, processed_at)` table feeds the Neo4j, OpenSearch and Qdrant projection workers.
- Row-level security for review tables by role. `review_audit` is append-only, enforced by a trigger.
- `CHECK (assertion <> 'inferred' OR origin = 'ai_generated')` on `fact` and `relationship` (ADR-010).
- `CHECK (confidence BETWEEN 0 AND 1)`.

```sql
CREATE TABLE fact (
  fact_id TEXT PRIMARY KEY, unit_id TEXT NOT NULL REFERENCES knowledge_unit(unit_id),
  predicate TEXT NOT NULL, object JSONB, origin TEXT NOT NULL, assertion TEXT NOT NULL,
  confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  sensitive TEXT[] DEFAULT '{}', review_status TEXT NOT NULL, provenance JSONB NOT NULL,
  CHECK (assertion <> 'inferred' OR origin = 'ai_generated'));
```

---

## 21. JSON Schema export

- `ilm-engine schema export --out schemas/` writes `model_json_schema()` for every top-level model: `CanonicalBook`, `Anchor`, `Issue`, `DocumentReport`, `Section`, `OriginSpan`, `BookMetadata`, `Annotation`, `Citation`, `InternalRef`, `Work`, `WorkRelation`, `KnowledgeUnit`, `Fact`, `Entity`, `Relationship`, `ValidationResult`, `ReviewItem`, `ReviewDecision`, `RunManifest`, plus one per genre payload.
- The exported schemas are committed. A test fails if the models change without re-exporting them, which acts as a contract check for downstream consumers.
- LLM structured-output calls use the genre payload schemas as their `response_format` / tool input schema (ADR-006).
