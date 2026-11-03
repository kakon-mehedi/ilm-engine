"""Seerah: events of the Prophet's life."""

from __future__ import annotations

from ilm_engine.extractors.genres._base import Payload

GENRE = "seerah"
SUB_TYPES = ("event",)
UNIT_TYPES = ("event",)
prompt_task = "extract_seerah"


class Person(Payload):
    entity_id: str | None = None
    name: str | None = None
    role: str | None = None


class UnitSchema(Payload):
    event: str
    date_hijri: int | None = None
    place: str | None = None
    persons: list[Person] = []
    sequence_hint: str | None = None


sensitive_fields: dict[str, str] = {}
