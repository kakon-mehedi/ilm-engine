"""History: dated events of Islamic history."""

from __future__ import annotations

from ilm_engine.extractors.genres._base import Date, Payload

GENRE = "history"
SUB_TYPES = ("event",)
UNIT_TYPES = ("event",)
prompt_task = "extract_history"


class UnitSchema(Payload):
    event: str
    date: Date | None = None
    place: str | None = None
    persons: list[str] = []
    chronology_order: int | None = None
    dynasty: str | None = None
    source_claim: str | None = None


sensitive_fields: dict[str, str] = {}
