"""Biography (sub-type ansab for the sample): one biographical entry per person."""

from __future__ import annotations

from typing import Literal

from ilm_engine.extractors.genres._base import Payload

GENRE = "biography"
SUB_TYPES = ("ansab", "tabaqat", "tarajim")
UNIT_TYPES = ("biographical_entry",)
prompt_task = "entry_facts"


class Person(Payload):
    surface: str
    span: list[int] | None = None  # [start, end] in the entry block
    ism: str | None = None
    kunya: str | None = None
    laqab: str | None = None
    nisba: list[str] = []
    gender: Literal["m", "f", "unknown"] = "unknown"


class LifeEvent(Payload):
    year_hijri: int | None = None
    place: str | None = None


class Relative(Payload):
    relation: str
    entity_id: str | None = None
    name: str | None = None
    kind: str | None = None


class UnitSchema(Payload):
    entry_no: int | None = None
    person: Person
    nasab: list[str] = []
    kunya: str | None = None
    laqab: str | None = None
    birth: LifeEvent | None = None
    death: LifeEvent | None = None
    teachers: list[str] = []
    students: list[str] = []
    relatives: list[Relative] = []
    companion_status: Literal["sahabi", "not_sahabi", "unknown"] = "unknown"
    narration_status: bool | None = None  # has narration
    section_heading_block: str | None = None
    tarjama_annotation: str | None = None  # footnote block of the entry's biography note


sensitive_fields: dict[str, str] = {}
