"""Sensitive content (ADR-009, DECISIONS §8): items that always go to scholar review.

Tags come from rules, never from a model's opinion:
- `hadith_grading`: a grading word next to an isnad term ("وإسناده ضعيف", "حديث صحيح");
- `prophetic_attribution`: Prophetic-speech formulas ("قال رسول الله") and span class c1 (inferred
  meaning `prophetic_speech`, DECISIONS §12c);
- `fiqh_ruling` / `aqeedah_proposition`: ruling and creed lexicons, applied in books of that genre, and
  any genre-payload field a plugin declares sensitive (ADR-013);
- `narrator_disambiguation`: set by entity linking when one name may be several narrators.
A tagged item gets `pending_review` and issue `sensitive_content` whatever its confidence.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ilm_engine.canonical.models import Block
from ilm_engine.enrichment.issues import make_issue
from ilm_engine.enrichment.models import Anchor, Issue, ReviewStatus, SensitiveCategory

STEP = "validate"
SPAN_MEANINGS = {
    "c2": "footnote_marker",
    "c5": "emphasis",
    "c1": "prophetic_speech",
    "c4": "editor_bracket_heading",
}

_LEXICONS: dict[str, re.Pattern[str]] = {
    "hadith_grading": re.compile(
        r"(?:و?إسناده|و?سنده|و?الحديث|حديث|رجاله)\s+(?:صحيح|حسن|ضعيف(?:\s+جدا)?|موضوع|منكر|ثقات)"
    ),
    "prophetic_attribution": re.compile(
        r"(?:قال|يقول|سمعت)\s+(?:رسول\s+الله|النبي|رسول\s+اللَّه)|عن\s+النبي\s*-?\s*صلى"
    ),
}
_GENRE_LEXICONS: dict[str, tuple[str, re.Pattern[str]]] = {
    "fiqh": ("fiqh_ruling", re.compile(r"\b(?:يجب|يحرم|حرام|واجب|يستحب|مستحب|مكروه|لا يجوز|يجوز)\b")),
    "aqeedah": ("aqeedah_proposition", re.compile(r"\b(?:يعتقد|الاعتقاد|أهل السنة|كفر|بدعة)\b")),
}


@dataclass(frozen=True)
class SensitiveTag:
    category: SensitiveCategory
    rule: str  # lexicon | span_class | schema_field | entity_linking
    anchor: Anchor | None = None


def tag_block(block: Block, pub_ref: str, scan_page: int, genres: Iterable[str] = ()) -> list[SensitiveTag]:
    """Sensitive tags found in one block's text and spans, with anchors."""

    def anchor(start: int, end: int) -> Anchor:
        return Anchor(
            pub_ref=pub_ref,
            page=block.page,
            scan_page=scan_page,
            block_id=block.block_id,
            start=start,
            end=end,
            quote=block.text[start:end],
            block_hash=block.block_hash,
        )

    tags = [
        SensitiveTag(category, "lexicon", anchor(match.start(), match.end()))  # type: ignore[arg-type]
        for category, pattern in _LEXICONS.items()
        for match in pattern.finditer(block.text)
    ]
    for genre in genres:
        if genre in _GENRE_LEXICONS:
            category, pattern = _GENRE_LEXICONS[genre]
            tags += [
                SensitiveTag(category, "lexicon", anchor(m.start(), m.end()))  # type: ignore[arg-type]
                for m in pattern.finditer(block.text)
            ]
    tags += [
        SensitiveTag("prophetic_attribution", "span_class", anchor(span.start, span.end))
        for span in block.spans
        if SPAN_MEANINGS.get(span.cls) == "prophetic_speech"
    ]
    return tags


def payload_categories(payload: Mapping[str, Any], sensitive_fields: Mapping[str, str]) -> list[str]:
    """Categories of the genre-payload fields a plugin declares sensitive and that hold a value."""
    return sorted({category for name, category in sensitive_fields.items() if payload.get(name) is not None})


def categories(tags: Iterable[SensitiveTag]) -> list[SensitiveCategory]:
    return sorted({tag.category for tag in tags})


def enforce(review_status: ReviewStatus, sensitive: Iterable[str]) -> ReviewStatus:
    """Sensitive items are never auto-approved."""
    return "pending_review" if list(sensitive) and review_status == "auto_approved" else review_status


def sensitive_issue(
    pub_ref: str, target_kind: str, target_id: str, sensitive: Iterable[str], anchors: Iterable[Anchor] = ()
) -> Issue:
    found = sorted(set(sensitive))
    return make_issue(
        pub_ref,
        "sensitive_content",
        "info",
        target_kind,
        target_id,
        f"Sensitive content ({', '.join(found)}): requires a scholar reviewer.",
        STEP,
        details={"categories": found},
        anchors=list(anchors),
    )
