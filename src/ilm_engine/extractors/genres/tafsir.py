"""Tafsir: explanation of Quranic verses."""

from __future__ import annotations

from ilm_engine.extractors.genres._base import Payload, QuotedRef

GENRE = "tafsir"
SUB_TYPES = ("tafsir_unit",)
UNIT_TYPES = ("tafsir_unit",)
prompt_task = "extract_tafsir"


class AyahRef(Payload):
    surah: int
    ayah_from: int
    ayah_to: int | None = None


class Qawl(QuotedRef):
    mufassir: str | None = None
    view: str | None = None


class UnitSchema(Payload):
    ayah_ref: AyahRef
    tafsir_text: str | None = None
    aqwal: list[Qawl] = []
    mufassir: str | None = None
    method: str | None = None  # bi'l-ma'thur | bi'l-ra'y


sensitive_fields: dict[str, str] = {}
