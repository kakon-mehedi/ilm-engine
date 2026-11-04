"""Hadith: matn, isnad, takhrij and grading. The MVP parses takhrij footnotes (ADR-013)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import Field

from ilm_engine.extractors.genres._base import Payload, QuotedRef, SourceRef
from ilm_engine.nlp.arabic_digits import to_int

GENRE = "hadith"
SUB_TYPES = ("hadith", "takhrij")
UNIT_TYPES = ("hadith", "hadith_takhrij")
prompt_task = "extract_hadith"


class Rawi(Payload):
    name: str
    link_word: str | None = None  # حدثنا | أخبرنا | عن
    entity_id: str | None = None
    position: int | None = None


class Grading(QuotedRef):
    label: Literal["sahih", "hasan", "daif", "daif_jiddan", "mawdu", "other"]
    label_raw: str  # as written, e.g. "ضعيف"
    grader: str | None = None
    reason: str | None = None


class UnitSchema(Payload):
    matn: str | None = Field(
        default=None, json_schema_extra={"sensitive": True, "sensitive_category": "prophetic_attribution"}
    )
    isnad: list[Rawi] = []
    takhrij: list[SourceRef] = []
    grading: Grading | None = Field(
        default=None, json_schema_extra={"sensitive": True, "sensitive_category": "hadith_grading"}
    )
    sharh_ref: str | None = None


sensitive_fields = {"grading": "hadith_grading", "matn": "prophetic_attribution"}

_GRADES = [
    ("ضعيف جدا", "daif_jiddan"),
    ("ضعيف", "daif"),
    ("صحيح", "sahih"),
    ("حسن", "hasan"),
    ("موضوع", "mawdu"),
]
_COLLECTED = re.compile(
    r"(?:و?رواه|و?أخرجه)\s+(?P<collector>[^\"«(]+?)\s+في\s+[\"«](?P<work>[^\"»]+)[\"»]\s*"
    r"(?:\((?P<vol>[٠-٩0-9]+)\s*/\s*(?P<page>[٠-٩0-9]+)\))?\s*(?:\(رقم:\s*(?P<num>[٠-٩0-9]+)\))?"
)
_GRADING = re.compile(
    r"(?:و?إسناده|و?سنده|والحديث|وهو)\s+(?P<grade>ضعيف جدا|ضعيف|صحيح|حسن|موضوع)(?P<reason>[^.،]*)"
)


def parse_takhrij(text: str) -> UnitSchema | None:
    """Takhrij references and the grading statement of a footnote; None if it has neither."""
    refs = [
        SourceRef(
            work=match["work"].strip(),
            collector=match["collector"].strip(),
            volume=to_int(match["vol"]) if match["vol"] else None,
            page=to_int(match["page"]) if match["page"] else None,
            number=to_int(match["num"]) if match["num"] else None,
            quote=match.group(0).strip(),
        )
        for match in _COLLECTED.finditer(text)
    ]
    grading = None
    if found := _GRADING.search(text):
        raw = found["grade"]
        grading = Grading(
            label=dict(_GRADES).get(raw, "other"),  # type: ignore[arg-type]
            label_raw=raw,
            grader="editor",
            reason=found["reason"].strip() or None,
            quote=found.group(0).strip(),
        )
    if not refs and grading is None:
        return None
    return UnitSchema(takhrij=refs, grading=grading)


def sensitive_categories(unit: UnitSchema) -> list[str]:
    """ADR-009 categories present in a hadith payload."""
    return sorted(
        category for field, category in sensitive_fields.items() if getattr(unit, field) is not None
    )
