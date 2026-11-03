"""Bibliographic metadata (step `metadata`, FR-020–FR-022).

Every field is a `MetadataField` with its value, where it came from (`sources`: existing metadata path
and/or anchors in the book) and how sure we are. Values from the source card are taken as stated by
the edition; content-derived values and conflicts are added on top (T-041, T-042).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.config import Config
from ilm_engine.enrichment.issues import make_issue
from ilm_engine.enrichment.models import Anchor, BookMetadata, Issue, MetadataField, MetadataSource, Origin
from ilm_engine.nlp.arabic_digits import to_int, words_to_int
from ilm_engine.nlp.normalize import normalize
from ilm_engine.processors.structure import Structure
from ilm_engine.validation.confidence import decide, score

STEP = "metadata"
ATTRIBUTES = "metadata.source_attributes"

_ORDINALS = {
    "الأولى": 1,
    "الاولى": 1,
    "الثانية": 2,
    "الثالثة": 3,
    "الرابعة": 4,
    "الخامسة": 5,
    "السادسة": 6,
    "السابعة": 7,
    "الثامنة": 8,
    "التاسعة": 9,
    "العاشرة": 10,
}
_EDITION_YEAR = re.compile(r"([٠-٩0-9]{3,4})\s*(هـ|م)")
_ARABIC_LETTER = re.compile(r"[ء-ي]")
_LATIN_LETTER = re.compile(r"[A-Za-z]")


def parse_edition(text: str) -> dict[str, int | None]:
    """'الأولى، ١٤١٣ هـ - ١٩٩٣ م' → {number: 1, year_hijri: 1413, year_gregorian: 1993}."""
    number = next((value for word, value in _ORDINALS.items() if word in text), None)
    years: dict[str, int | None] = {"year_hijri": None, "year_gregorian": None}
    for digits, era in _EDITION_YEAR.findall(text):
        years["year_hijri" if era == "هـ" else "year_gregorian"] = to_int(digits)
    return {"number": number, **years}


def detect_language(book: CanonicalBook) -> str:
    """'ar' when Arabic letters dominate the text, else 'und' (EC-008)."""
    text = "".join(block.text for block in book.blocks.values())
    arabic, latin = len(_ARABIC_LETTER.findall(text)), len(_LATIN_LETTER.findall(text))
    return "ar" if arabic > 2 * latin else "und"


class _Fields:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.rule_confidence = score(config, "rule").score

    def stated(
        self,
        value: Any,
        path: str | None,
        normalized: Any = None,
        kind: str = "existing_metadata",
    ) -> MetadataField:
        return MetadataField(
            value=value,
            normalized=normalized,
            sources=[MetadataSource(kind=kind, path=path)] if path or kind != "existing_metadata" else [],  # type: ignore[arg-type]
            assertion="stated",
            origin="editor_text",
            confidence=self.rule_confidence,
            review_status=decide(self.config, self.rule_confidence),
        )

    def unknown(self) -> MetadataField:
        return MetadataField(
            value=None,
            sources=[],
            assertion="stated",
            origin="editor_text",
            confidence=0.0,
            review_status="pending_review",
        )


def card_metadata(book: CanonicalBook, config: Config) -> tuple[BookMetadata, list[Issue]]:
    """Metadata from the source card and source attributes (T-040)."""
    meta = book.metadata
    fields = _Fields(config)
    edition = (
        parse_edition(meta.edition)
        if meta.edition
        else {"number": None, "year_hijri": None, "year_gregorian": None}
    )

    def field_or_unknown(value: Any, path: str, normalized: Any = None) -> MetadataField:
        return fields.stated(value, path, normalized) if value is not None else fields.unknown()

    author_value = (
        {"name": meta.author_name, "death_hijri": meta.author_death_hijri, "as_source": meta.author_as_source}
        if meta.author_name or meta.author_as_source
        else None
    )
    volumes = sorted({page.volume for page in book.pages})
    year_hijri = meta.year_hijri if meta.year_hijri is not None else edition["year_hijri"]
    year_gregorian = meta.year_gregorian if meta.year_gregorian is not None else edition["year_gregorian"]

    record = {
        "title": field_or_unknown(meta.title_as_source, "metadata.identity.title_as_source"),
        "author": field_or_unknown(author_value, f"{ATTRIBUTES}.author"),
        "editor": field_or_unknown(meta.editor, f"{ATTRIBUTES}.editor"),
        "publisher": field_or_unknown(meta.publisher, f"{ATTRIBUTES}.publisher"),
        "edition": field_or_unknown(meta.edition, f"{ATTRIBUTES}.edition", edition),
        "year_hijri": field_or_unknown(year_hijri, "editions.0.year_hijri"),
        "year_gregorian": field_or_unknown(year_gregorian, "editions.0.year_gregorian"),
        "volumes": fields.stated(len(volumes), "content.pages.volume", {"volumes": volumes}),
        "language": fields.stated(detect_language(book), None, kind="book_content"),
        "category": field_or_unknown(meta.category_name, "pub.category.name", {"id": meta.category_id}),
    }
    if meta.claimed_page_count is not None:
        record["edition"] = record["edition"].model_copy(
            update={"normalized": {**edition, "declared_pages": meta.claimed_page_count}}
        )
    missing = sorted(name for name, value in record.items() if value.value is None)
    metadata = BookMetadata(
        pub_ref=book.book.pub_ref,
        title_variants=[meta.title_as_source] if meta.title_as_source else [],
        genre_primary=fields.unknown(),  # filled by the genre step (T-095)
        genre_secondary=[],
        missing_fields=missing,
        issues=[],
        **record,
    )
    return metadata, []


# --- Metadata from the book's own text (T-041) -------------------------------------------------------

_DEATH = re.compile(r"(?:توف[ِّ]*[يى]|المتوفى|مات)")
_YEAR_PHRASE = re.compile(r"سنة[ٍَُِ]*\s*(?:\(\s*[٠-٩0-9]+\s*\)|[٠-٩0-9]+|[^،.()]+)")
_DIGITS = re.compile(r"[٠-٩0-9]+")
_PART = re.compile(r"«?\s*الجزء\s+(الأول|الثاني|الثالث|الرابع)\s*»?")
_MISSING_PART = re.compile(r"لم\s+أجد\s+الجزء\s+(الثاني|الثالث|الرابع)")
_PART_NUMBERS = {"الأول": 1, "الثاني": 2, "الثالث": 3, "الرابع": 4}


def _anchor(book: CanonicalBook, block_id: str, start: int, end: int) -> Anchor:
    block = book.block(block_id)
    while end > start and block.text[end - 1].isspace():
        end -= 1
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


def _year(phrase: str) -> int | None:
    digits = _DIGITS.search(phrase)
    if digits:
        return to_int(digits.group(0))
    try:
        return words_to_int(phrase)
    except ValueError:
        return None


@dataclass
class ContentFinding:
    field: str
    value: Any
    anchors: list[Anchor]
    origin: Origin


def death_year_findings(
    book: CanonicalBook, origins: dict[str, Origin], structure: Structure
) -> list[ContentFinding]:
    """Author death years stated on the title page or in the section about the author."""
    author_words = {normalize(word) for word in (book.metadata.author_name or "").split() if len(word) > 3}
    about_author = {
        section.section_id
        for section in structure.sections
        if section.level > 0 and author_words & set(normalize(section.title).split())
    }
    title_page = book.pages[0].n if book.pages else None
    findings = []
    for block in book.blocks_in_order():
        on_title_page = block.page == title_page and block.kind == "text"
        in_section = structure.block_section.get(block.block_id) in about_author
        if block.kind == "footnote" or not (on_title_page or in_section):
            continue
        for death in _DEATH.finditer(block.text):
            phrase = _YEAR_PHRASE.search(block.text, death.end())
            if phrase is None or phrase.start() - death.end() > 40:
                continue
            year = _year(phrase.group(0))
            if year is not None:
                anchor = _anchor(book, block.block_id, phrase.start(), phrase.end())
                findings.append(
                    ContentFinding(
                        "author.death_hijri", year, [anchor], origins.get(block.block_id, "editor_text")
                    )
                )
                break
    return findings


def title_page_findings(book: CanonicalBook, origins: dict[str, Origin]) -> list[ContentFinding]:
    """Title, author and editor as printed on the title page (first page of the source)."""
    if not book.pages:
        return []
    blocks = [
        book.block(block_id) for block_id in book.pages[0].block_ids if book.block(block_id).kind == "text"
    ]
    findings = []
    if blocks:
        findings.append(
            ContentFinding(
                "title",
                blocks[0].text,
                [_anchor(book, blocks[0].block_id, 0, len(blocks[0].text))],
                origins.get(blocks[0].block_id, "editor_text"),
            )
        )
    for index, block in enumerate(blocks[:-1]):
        label, value = normalize(block.text), blocks[index + 1]
        anchor = [_anchor(book, value.block_id, 0, len(value.text))]
        if label in {normalize("للحافظ"), normalize("تأليف"), normalize("للإمام")}:
            findings.append(
                ContentFinding("author.name", value.text, anchor, origins.get(value.block_id, "editor_text"))
            )
        elif label in {normalize("تحقيق"), normalize("حققه")}:
            findings.append(
                ContentFinding("editor", value.text, anchor, origins.get(value.block_id, "editor_text"))
            )
    return findings


def volume_findings(book: CanonicalBook, origins: dict[str, Origin]) -> ContentFinding | None:
    """«الجزء الأول» plus "لم أجد الجزء الثاني" → part 1 of at least 2."""
    part, anchors, at_least = None, [], None
    for block in book.blocks_in_order():
        if part is None and (match := _PART.search(block.text)) and block.page == book.pages[0].n:
            part = _PART_NUMBERS[match.group(1)]
            anchors.append(_anchor(book, block.block_id, match.start(), match.end()))
        if match := _MISSING_PART.search(block.text):
            at_least = _PART_NUMBERS[match.group(1)]
            anchors.append(_anchor(book, block.block_id, match.start(), match.end()))
    if part is None:
        return None
    value = {"part": part, "of_at_least": max(at_least or part, part)}
    return ContentFinding("volume_note", value, anchors, "editor_text")


def content_metadata(
    book: CanonicalBook,
    record: BookMetadata,
    origins: dict[str, Origin],
    structure: Structure,
    config: Config,
    llm_available: bool = False,
) -> tuple[BookMetadata, list[ContentFinding], list[Issue]]:
    """Add content-derived evidence to the card record (sources `book_content` with anchors)."""
    findings = [
        *title_page_findings(book, origins),
        *death_year_findings(book, origins, structure),
    ]
    volume = volume_findings(book, origins)
    updates: dict[str, Any] = {}

    def with_content(field: MetadataField, anchors: list[Anchor]) -> MetadataField:
        return field.model_copy(
            update={"sources": [*field.sources, MetadataSource(kind="book_content", anchors=anchors)]}
        )

    for finding in findings:
        name, _, key = finding.field.partition(".")
        current = updates.get(name, getattr(record, name))
        if key and isinstance(current.value, dict) and current.value.get(key) is None:
            current = current.model_copy(
                update={"value": {**current.value, key: finding.value}}
            )  # card lacked it
        updates[name] = with_content(current, finding.anchors)

    if volume is not None:
        fields = _Fields(config)
        updates["volume_note"] = fields.stated(volume.value, None, kind="book_content").model_copy(
            update={"sources": [MetadataSource(kind="book_content", anchors=volume.anchors)]}
        )
        findings.append(volume)
    issues = []
    if not llm_available:
        issues.append(
            make_issue(
                book.book.pub_ref,
                "needs_llm",
                "info",
                "book",
                book.book.pub_ref,
                "Metadata LLM verification (metadata_verify) not run: no LLM provider configured.",
                STEP,
                details={"task": "metadata_verify"},
            )
        )
    return record.model_copy(update=updates), findings, issues
