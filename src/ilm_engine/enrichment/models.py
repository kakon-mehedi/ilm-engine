"""Enrichment layer models (03-data-contracts §1, §3–18).

Every module imports these instead of defining its own records. The enrichment layer is separate from
the canonical book (ADR-001): it points into the original text through `Anchor`s and never copies or
modifies it. Genre payload models live with the genre plugins (`extractors/genres/`, T-095).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from ilm_engine.canonical.models import SHA256_PATTERN, SourceQuality, Strict

ENRICHMENT_SCHEMA_VERSION: Literal["1.0"] = "1.0"

# §1 Common types

Origin = Literal["author_text", "transmission_isnad", "editor_text", "editor_footnote", "ai_generated"]
Assertion = Literal["stated", "inferred"]
Genre = Literal["fiqh", "hadith", "tafsir", "seerah", "aqeedah", "history", "biography"]
ReviewStatus = Literal[
    "auto_approved", "pending_review", "approved", "rejected", "edited", "reprocess_requested"
]
Severity = Literal["info", "warning", "error"]
SensitiveCategory = Literal[
    "prophetic_attribution", "hadith_grading", "fiqh_ruling", "aqeedah_proposition", "narrator_disambiguation"
]
ExtractionMethod = Literal["structural", "rule", "nlp", "llm", "llm_consensus", "human"]

IssueCode = Literal[
    "unknown_schema_version",
    "page_count_mismatch",
    "missing_page",
    "toc_without_block",
    "toc_page_offset",
    "heading_without_toc",
    "unlinked_footnote",
    "nested_footnote",
    "continued_footnote_joined",
    "broken_ref",
    "numbering_gap",
    "numbering_duplicate",
    "entry_without_footnote",
    "title_variant",
    "metadata_conflict",
    "evidence_not_found",
    "schema_invalid",
    "model_disagreement",
    "ambiguous_entity",
    "needs_llm",
    "sensitive_content",
    "unresolved_internal_ref",
    "anchor_stale",
    "source_hash_unverified",
]

PersonRelType = Literal[
    "child_of",
    "parent_of",
    "sibling_of",
    "spouse_of",
    "mother_is",
    "teacher_of",
    "student_of",
    "narrated_from",
]
WorkRelType = Literal[
    "sharh_of",
    "hashiyah_of",
    "mukhtasar_of",
    "translation_of",
    "edition_of",
    "tahqiq_of",
    "cites",
    "same_topic_as",
]
SiblingKind = Literal["full", "paternal", "maternal", "unknown"]

Confidence = Annotated[float, Field(ge=0, le=1)]


class Provenance(Strict):
    """How a value was produced. Attached to every derived record."""

    method: ExtractionMethod
    step: str
    step_version: str
    model_id: str | None = None
    prompt_id: str | None = None
    prompt_version: str | None = None


def _check_inferred_origin(assertion: Assertion, origin: Origin, record: str) -> None:
    # ADR-010: anything the system infers is the system's statement, never the author's.
    if assertion == "inferred" and origin != "ai_generated":
        raise ValueError(f"{record}: an inferred assertion must have origin 'ai_generated', got {origin!r}")


# §3 Anchor


class Anchor(Strict):
    """Pointer to an exact span of an original block. `block.text[start:end] == quote` is checked by
    `validation/evidence.py`, which needs the block text."""

    pub_ref: str
    page: int
    scan_page: int
    block_id: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    quote: str
    quote_truncated: bool = False
    block_hash: str = Field(pattern=SHA256_PATTERN)
    status: Literal["valid", "stale", "orphaned"] = "valid"
    bbox: list[float] | None = None

    @model_validator(mode="after")
    def _ordered_offsets(self) -> Self:
        if self.start > self.end:
            raise ValueError(f"anchor on {self.block_id}: start {self.start} > end {self.end}")
        return self


# §4 Issue


class Issue(Strict):
    issue_id: str
    code: IssueCode
    severity: Severity
    target_kind: Literal[
        "book",
        "page",
        "block",
        "section",
        "annotation",
        "citation",
        "unit",
        "fact",
        "entity",
        "relationship",
        "metadata_field",
        "work",
    ]
    target_id: str
    message: str
    anchors: list[Anchor] = []
    details: dict[str, Any] = {}
    provenance: Provenance


# §5 Document report


class DocumentReport(Strict):
    pub_ref: str
    page_count_held: int
    page_count_claimed: int | None
    printed_page_range: tuple[int, int]
    missing_printed_pages: list[int]
    pdf_page_count: int | None
    pdf_pages_not_in_json: list[int]
    block_counts: dict[str, int]
    block_total: int
    ref_count: int
    refs_from_footnotes: int
    continued_footnotes: int
    span_class_counts: dict[str, int]
    empty_blocks: list[str]
    duplicate_blocks: list[list[str]]
    source_quality: SourceQuality | None
    issues: list[str]
    page_classes: dict[str, str] = {}  # printed gaps and extra scan pages → class (T-031)


# §6 Section and origin


class Section(Strict):
    section_id: str
    title: str
    level: int = Field(ge=0)
    heading_block_id: str | None
    toc_index: int | None
    toc_source_page_key: str | None
    start_block_id: str
    end_block_id: str  # inclusive
    start_page: int
    end_page: int
    parent_id: str | None
    children: list[str] = []
    origin: Origin
    provenance: Provenance


class OriginSpan(Strict):
    """Contiguous run of blocks sharing an origin (origin_map.json)."""

    origin: Origin
    start_block_id: str
    end_block_id: str
    start_page: int
    end_page: int
    rule: str
    block_count: int = Field(ge=0)


# §7 Metadata with provenance


class MetadataSource(Strict):
    kind: Literal["existing_metadata", "book_content", "pdf_visual", "external_catalog"]
    path: str | None = None
    anchors: list[Anchor] = []


class MetadataField(Strict):
    value: Any
    normalized: Any | None = None
    sources: list[MetadataSource]
    assertion: Assertion
    origin: Origin
    confidence: Confidence
    conflicts: list[dict[str, Any]] = []
    review_status: ReviewStatus


class BookMetadata(Strict):
    pub_ref: str
    title: MetadataField
    title_variants: list[str]
    author: MetadataField
    editor: MetadataField
    publisher: MetadataField
    edition: MetadataField
    year_hijri: MetadataField
    year_gregorian: MetadataField
    volumes: MetadataField
    language: MetadataField
    category: MetadataField
    genre_primary: MetadataField
    genre_secondary: list[MetadataField]
    missing_fields: list[str]
    issues: list[str]
    volume_note: MetadataField | None = None  # e.g. {"part": 1, "of_at_least": 2} from the book's text


# §8 Annotation


class Annotation(Strict):
    annotation_id: str
    type: Literal["footnote", "endnote", "sidenote", "nested_footnote"]
    source_block_id: str
    marker_anchor: Anchor
    target_block_ids: list[str]
    marker_text: str | None
    link_method: Literal["source_ref", "marker_match", "llm_candidate"]
    is_entry_note: bool
    status: Literal["verified", "candidate", "unlinked"]
    origin: Origin = "editor_footnote"
    provenance: Provenance


# §9 Citation and internal reference


class Locator(Strict):
    raw: str
    volume: int | None
    page: int | None
    number: int | None = None
    page_label: str | None = None


class Citation(Strict):
    citation_id: str
    title_raw: str
    title_normalized: str
    work_id: str | None
    author_hint: str | None
    locators: list[Locator]
    anchor: Anchor
    context: Literal["footnote", "body"]
    origin: Origin
    resolution: Literal["alias_table", "agent", "unresolved"]
    confidence: Confidence
    provenance: Provenance


class InternalRef(Strict):
    internal_ref_id: str
    kind: Literal["entry_number", "forward", "backward"]
    anchor: Anchor
    target_unit_id: str | None
    target_entry_no: int | None
    status: Literal["resolved", "unresolved"]
    provenance: Provenance


# §10 Work and work relation


class Work(Strict):
    work_id: str = Field(pattern=r"^wrk_[0-9a-f]{12}$")  # ours; source work IDs go in source_work_id
    source_work_id: str | None
    title: str
    title_normalized: str
    aliases: list[str]
    author_name: str | None
    author_entity_id: str | None
    status: Literal["catalog", "stub", "this_book"]


class WorkRelation(Strict):
    relation_id: str
    type: WorkRelType
    subject_work_id: str
    object_work_id: str
    evidence: list[Anchor]
    origin: Origin
    assertion: Assertion
    confidence: Confidence
    count: int = Field(default=1, ge=1)
    review_status: ReviewStatus
    provenance: Provenance

    @model_validator(mode="after")
    def _inferred_is_ai(self) -> Self:
        _check_inferred_origin(self.assertion, self.origin, self.relation_id)
        return self


# §11 Fact and knowledge unit


class Fact(Strict):
    fact_id: str  # "ku_<12hex>#f<N>"
    predicate: str
    object: Any
    object_entity_id: str | None = None
    evidence: list[Anchor] = Field(min_length=1)
    origin: Origin
    assertion: Assertion
    confidence: Confidence
    sensitive: list[SensitiveCategory] = []
    review_status: ReviewStatus
    provenance: Provenance

    @model_validator(mode="after")
    def _inferred_is_ai(self) -> Self:
        _check_inferred_origin(self.assertion, self.origin, self.fact_id)
        return self


class KnowledgeUnit(Strict):
    unit_id: str
    genre: Genre
    sub_type: str | None
    unit_type: str
    entry_no: int | None
    section_id: str
    anchors: list[Anchor]
    note_annotation_ids: list[str]
    subject_entity_id: str | None
    payload: dict[str, Any]
    facts: list[Fact]
    origin: Origin
    confidence: Confidence
    review_status: ReviewStatus
    issues: list[str]
    provenance: Provenance


# §13 Entity


class PersonName(Strict):
    ism: str | None = None
    kunya: str | None = None
    laqab: str | None = None
    nisba: list[str] = []
    nasab: list[str] = []  # ancestors in order
    full_surface: str


class Entity(Strict):
    entity_id: str
    entity_type: Literal["person", "place", "work", "event", "concept", "group"]
    canonical_name: str
    canonical_name_normalized: str
    name: PersonName | None
    gender: Literal["m", "f", "unknown"] = "unknown"
    aliases: list[str] = []
    roles: list[Literal["author", "editor", "narrator", "sahabi", "scholar", "subject"]] = []
    mentions: list[Anchor]
    external_ids: dict[str, str] = {}
    disambiguation: Literal["unique", "resolved", "ambiguous"] = "unique"
    candidates: list[str] = []
    confidence: Confidence
    review_status: ReviewStatus
    provenance: Provenance


# §14 Relationship


class RelationshipAttrs(Strict):
    kind: SiblingKind | None = None
    via_parent_entity_id: str | None = None
    group_id: str | None = None
    # "لأم ولد" → umm_walad, which is NOT kind=maternal (DECISIONS §11).
    mother_status: Literal["umm_walad", "named", "unknown"] | None = None


class Relationship(Strict):
    relation_id: str
    type: PersonRelType
    subject_entity_id: str
    object_entity_id: str
    attrs: RelationshipAttrs = RelationshipAttrs()
    evidence: list[Anchor] = Field(min_length=1)
    origin: Origin
    assertion: Assertion
    confidence: Confidence
    sensitive: list[SensitiveCategory] = []
    review_status: ReviewStatus
    provenance: Provenance

    @model_validator(mode="after")
    def _inferred_is_ai(self) -> Self:
        _check_inferred_origin(self.assertion, self.origin, self.relation_id)
        return self


# §15 Validation result


class ConfidenceFactors(Strict):
    base: float
    evidence: float
    schema_: float = Field(alias="schema")
    agreement: float
    penalties: dict[str, float] = {}


class ValidationResult(Strict):
    target_kind: str
    target_id: str
    schema_valid: bool
    evidence_found: bool
    evidence_match: Literal["exact", "normalized", "none"]
    model_outputs: list[dict[str, Any]] = []
    agreement: Literal["agree", "disagree", "judge_resolved", "single"] = "single"
    factors: ConfidenceFactors
    confidence: Confidence
    sensitive: list[SensitiveCategory] = []
    threshold: Confidence
    decision: ReviewStatus
    issues: list[str] = []


# §16 Review item and decision


class ReviewItem(Strict):
    review_id: str
    target_kind: str
    target_id: str
    reason: list[Literal["low_confidence", "sensitive", "discrepancy", "needs_llm", "structural_issue"]]
    sensitive: list[SensitiveCategory] = []
    required_role: Literal["editor_reviewer", "scholar_reviewer"]
    priority: int = Field(ge=0)
    confidence: Confidence | None
    proposed_value: Any
    model_outputs: list[dict[str, Any]] = []
    anchors: list[Anchor]
    context_block_ids: list[str]
    pdf: dict[str, Any]
    issues: list[str]
    status: ReviewStatus = "pending_review"

    @model_validator(mode="after")
    def _sensitive_needs_scholar(self) -> Self:
        # DECISIONS §12c: any sensitive category requires a scholar reviewer.
        if self.sensitive and self.required_role != "scholar_reviewer":
            raise ValueError(f"{self.review_id}: sensitive items require required_role 'scholar_reviewer'")
        return self


class ReviewDecision(Strict):
    review_id: str
    decision: Literal["approved", "rejected", "edited", "reprocess_requested"]
    new_value: Any | None = None
    reviewer_id: str
    reviewer_role: Literal["editor_reviewer", "scholar_reviewer", "admin"]
    reason: str | None = None
    decided_at: str  # ISO 8601; audit records only, never content files


# §17 Run manifest


class FileHash(Strict):
    path: str
    sha256: str
    bytes: int = Field(ge=0)


class StepRecord(Strict):
    name: str
    version: str
    status: Literal["ran", "cached", "skipped", "failed"]
    cache_key: str
    duration_ms: int = Field(ge=0)
    outputs: list[str]


class RunManifest(Strict):
    run_id: str
    pub_ref: str
    started_at: str
    finished_at: str
    code_version: str
    config_hash: str
    canonical_schema_version: str
    enrichment_schema_version: str
    normalizer_version: str
    adapter: dict[str, str]
    llm: dict[str, Any]
    steps: list[StepRecord]
    inputs: list[FileHash]
    outputs: list[FileHash]
    integrity: dict[str, Any]
    counts: dict[str, int]


# §18 Consolidated enrichment.json


class EnrichmentSource(Strict):
    source_code: str
    schema_version: str
    adapter: str  # "shamela_v3@1.0.0"
    canonical_content_hash: str
    source_declared_hash: str | None
    source_declared_hash_verified: bool


class Structure(Strict):
    root_section_id: str
    sections: list[Section]


class Enrichment(Strict):
    """`enrichment.json`: the merge of the per-type output files, each list sorted by ID."""

    enrichment_schema_version: Literal["1.0"] = ENRICHMENT_SCHEMA_VERSION
    pub_ref: str
    run_id: str
    source: EnrichmentSource
    document_report: DocumentReport
    metadata: BookMetadata
    structure: Structure
    origin_map: list[OriginSpan]
    annotations: list[Annotation]
    internal_refs: list[InternalRef]
    citations: list[Citation]
    works: list[Work]
    work_relations: list[WorkRelation]
    knowledge_units: list[KnowledgeUnit]
    entities: list[Entity]
    relationships: list[Relationship]
    validation: list[ValidationResult]
    issues: list[Issue]
    review_queue_ids: list[str]
    stats: dict[str, int]
