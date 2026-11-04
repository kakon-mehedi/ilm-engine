"""Aqeedah: creedal propositions with their evidence."""

from __future__ import annotations

from pydantic import Field

from ilm_engine.extractors.genres._base import Payload, QuotedRef

GENRE = "aqeedah"
SUB_TYPES = ("proposition",)
UNIT_TYPES = ("proposition",)
prompt_task = "extract_aqeedah"


class Evidence(QuotedRef):
    type: str | None = None  # quran | hadith | athar | reason
    ref: str | None = None


class UnitSchema(Payload):
    concept: str
    proposition: str | None = Field(
        default=None, json_schema_extra={"sensitive": True, "sensitive_category": "aqeedah_proposition"}
    )
    evidence: list[Evidence] = []
    school: str | None = None
    refuted_view: str | None = None


sensitive_fields = {"proposition": "aqeedah_proposition"}
