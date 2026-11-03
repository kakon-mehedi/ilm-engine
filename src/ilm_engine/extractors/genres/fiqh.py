"""Fiqh: legal questions (masala) with rulings, evidence and differences of opinion."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from ilm_engine.extractors.genres._base import Payload, QuotedRef

GENRE = "fiqh"
SUB_TYPES = ("masala",)
UNIT_TYPES = ("masala",)
prompt_task = "extract_fiqh"


class Hukm(Payload):
    label: str | None = None  # wajib | mandub | mubah | makruh | haram | sahih | batil | ...
    text: str | None = None


class Dalil(QuotedRef):
    type: Literal["quran", "hadith", "ijma", "qiyas", "athar"]
    ref: str | None = None


class Khilaf(Payload):
    madhhab: str | None = None
    scholar: str | None = None
    position: str | None = None
    dalil: str | None = None


class UnitSchema(Payload):
    masala: str
    hukm: Hukm | None = Field(
        default=None, json_schema_extra={"sensitive": True, "sensitive_category": "fiqh_ruling"}
    )
    dalil: list[Dalil] = []
    madhhab: str | None = None
    qail: str | None = None  # who holds the view (entity id or name)
    khilaf: list[Khilaf] = []
    rajih: str | None = None  # only if the author states the preferred view


sensitive_fields = {"hukm": "fiqh_ruling"}
