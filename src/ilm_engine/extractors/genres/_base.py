"""Shared pieces of the genre payload schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuotedRef(Payload):
    block_id: str | None = None
    quote: str | None = None  # verbatim from the source


class SourceRef(Payload):
    work: str | None = None
    collector: str | None = None
    volume: int | None = None
    page: int | None = None
    number: int | None = None
    quote: str | None = None


class Date(Payload):
    hijri: int | None = None
    gregorian: int | None = None
    precision: str | None = None  # year | month | day | approximate
