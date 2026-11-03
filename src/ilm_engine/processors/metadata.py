"""Bibliographic metadata (step `metadata`, FR-020–FR-022).

Every field is a `MetadataField` with its value, where it came from (`sources`: existing metadata path
and/or anchors in the book) and how sure we are. Values from the source card are taken as stated by
the edition; content-derived values and conflicts are added on top (T-041, T-042).
"""

from __future__ import annotations

import re
from typing import Any

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.config import Config
from ilm_engine.enrichment.models import BookMetadata, Issue, MetadataField, MetadataSource
from ilm_engine.nlp.arabic_digits import to_int
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
