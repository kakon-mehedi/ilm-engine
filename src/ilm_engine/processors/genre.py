"""Genre Router (step `genre`; the first agent of DECISIONS §12, here a deterministic function).

The source category is a strong prior (`الأنساب` → biography/ansab). Content signals add secondary
genres: takhrij formulas in the footnotes ("رواه … في", "إسناده ضعيف") → hadith. Every signal keeps
anchored evidence. The decision fills `metadata.genre_primary` / `genre_secondary`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.config import Config
from ilm_engine.enrichment.models import Anchor, MetadataField, MetadataSource
from ilm_engine.extractors.genres import registry
from ilm_engine.nlp.normalize import normalize
from ilm_engine.validation.confidence import decide, score
from ilm_engine.validation.evidence import locate

STEP = "genre"
MIN_SECONDARY_SIGNALS = 3
MAX_EVIDENCE = 3

# Source category (normalized) → (genre, sub-type).
CATEGORY_GENRES = {
    normalize("الأنساب"): ("biography", "ansab"),
    normalize("التراجم والطبقات"): ("biography", "tabaqat"),
    normalize("التراجم"): ("biography", "tarajim"),
    normalize("الفقه العام"): ("fiqh", None),
    normalize("الفقه"): ("fiqh", None),
    normalize("كتب السنة"): ("hadith", None),
    normalize("الحديث"): ("hadith", None),
    normalize("شروح الحديث"): ("hadith", None),
    normalize("التفسير"): ("tafsir", None),
    normalize("السيرة النبوية"): ("seerah", None),
    normalize("العقيدة"): ("aqeedah", None),
    normalize("التاريخ"): ("history", None),
}

# Content signals per genre, matched on footnotes and text: (name, pattern).
SIGNALS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    "hadith": [
        ("takhrij", re.compile(r"(?:رواه|أخرجه)\s+\S+(?:\s+\S+)?\s+في\s+[\"«]")),
        ("isnad_grading", re.compile(r"(?:إسناده|سنده)\s+(?:ضعيف|صحيح|حسن)")),
    ],
    "fiqh": [("ruling_terms", re.compile(r"\b(?:يجب|يستحب|يكره|يحرم|مسألة)\b"))],
    "tafsir": [("ayah_ref", re.compile(r"قوله تعالى"))],
}


@dataclass
class GenreDecision:
    primary: str | None
    sub_type: str | None
    secondary: list[str]
    signals: dict[str, dict[str, int]]  # genre → signal name → count
    confidence: float
    evidence: dict[str, list[Anchor]] = field(default_factory=dict)  # genre → anchored examples


def route(book: CanonicalBook, config: Config) -> GenreDecision:
    known = registry()
    category = normalize(book.metadata.category_name or "")
    primary, sub_type = CATEGORY_GENRES.get(category, (None, None))

    signals: dict[str, dict[str, int]] = {}
    evidence: dict[str, list[Anchor]] = {}
    scan_pages = {(page.volume, page.n): page.scan_page for page in book.pages}
    for genre, patterns in SIGNALS.items():
        counts: dict[str, int] = {}
        for name, pattern in patterns:
            for block in book.blocks_in_order():
                matches = list(pattern.finditer(block.text))
                if not matches:
                    continue
                counts[name] = counts.get(name, 0) + len(matches)
                if len(evidence.get(genre, [])) < MAX_EVIDENCE:
                    found = locate(
                        matches[0].group(0),
                        block,
                        pub_ref=book.book.pub_ref,
                        scan_page=scan_pages[(block.volume, block.page)],
                        hint_start=matches[0].start(),
                    )
                    if found is not None:
                        evidence.setdefault(genre, []).append(found.anchor)
        if counts:
            signals[genre] = counts

    secondary = sorted(
        genre
        for genre, counts in signals.items()
        if genre != primary and genre in known and sum(counts.values()) >= MIN_SECONDARY_SIGNALS
    )
    if primary is None and secondary:  # no category prior: strongest content signal, to be reviewed
        primary = max(secondary, key=lambda genre: sum(signals[genre].values()))
        secondary.remove(primary)
        confidence = score(config, "llm").score
    else:
        confidence = score(config, "rule").score if primary else 0.0
    return GenreDecision(primary, sub_type, secondary, signals, confidence, evidence)


def metadata_fields(decision: GenreDecision, config: Config) -> tuple[MetadataField, list[MetadataField]]:
    """`genre_primary` and `genre_secondary` metadata fields for the decision."""
    primary = MetadataField(
        value={"genre": decision.primary, "sub_type": decision.sub_type} if decision.primary else None,
        sources=[MetadataSource(kind="existing_metadata", path="pub.category.name")]
        if decision.sub_type
        else [],
        assertion="inferred",
        origin="ai_generated",
        confidence=decision.confidence,
        review_status=decide(config, decision.confidence) if decision.primary else "pending_review",
    )
    rule = score(config, "rule").score
    secondary = [
        MetadataField(
            value={"genre": genre, "signals": decision.signals[genre]},
            sources=[MetadataSource(kind="book_content", anchors=decision.evidence.get(genre, []))],
            assertion="inferred",
            origin="ai_generated",
            confidence=rule,
            review_status=decide(config, rule),
        )
        for genre in decision.secondary
    ]
    return primary, secondary
