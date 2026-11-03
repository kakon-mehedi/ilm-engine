"""Canonical book: the one internal shape every source adapter produces (03-data-contracts §1–2, ADR-002).

All models are frozen, so the original text cannot be mutated in memory. Text is stored exactly as the
source gives it; normalization happens elsewhere and never overwrites it.
"""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

CANONICAL_SCHEMA_VERSION: Literal["1.0"] = "1.0"

SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class Strict(BaseModel):
    """Base for every contract model: unknown fields rejected, instances immutable."""

    # Aliases (`class`, `schema`) are the contract names; they are used for both input and output.
    model_config = ConfigDict(extra="forbid", frozen=True, validate_by_name=True, serialize_by_alias=True)


BlockKind = Literal["text", "heading", "toc_heading", "footnote"]
SpanMeaning = Literal["footnote_marker", "emphasis", "prophetic_speech", "editor_bracket_heading", "unknown"]


class SourceInfo(Strict):
    source_code: str
    source_book_key: str
    schema_version: str
    source_adapter_semver: str | None
    adapter_id: str
    adapter_version: str
    claim_type: str | None
    source_declared_hash: str | None
    source_declared_hash_verified: bool = False


class BookRef(Strict):
    pub_id: str
    revision: int = Field(ge=0)
    pub_ref: str
    source_work_id: str | None
    edition_id: str | None

    @model_validator(mode="after")
    def _pub_ref_matches(self) -> Self:
        expected = f"{self.pub_id}@r{self.revision}"
        if self.pub_ref != expected:
            raise ValueError(f"pub_ref {self.pub_ref!r} does not match pub_id and revision ({expected!r})")
        return self


class Span(Strict):
    cls: str = Field(alias="class")
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str
    meaning: SpanMeaning = "unknown"


class Ref(Strict):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    to: str


class Block(Strict):
    block_id: str
    order: int = Field(ge=0)
    page: int
    volume: int
    kind: BlockKind
    text: str
    marker: str | None = None
    continues: bool = False
    refs: list[Ref] = []
    spans: list[Span] = []
    block_hash: str = Field(pattern=SHA256_PATTERN)
    raw_extras: dict[str, Any] = {}

    @model_validator(mode="after")
    def _offsets_inside_text(self) -> Self:
        items: list[Ref | Span] = [*self.refs, *self.spans]
        for item in items:
            if not item.start <= item.end <= len(self.text):
                bounds = f"[{item.start}, {item.end})"
                raise ValueError(f"{self.block_id}: offsets {bounds} outside text of length {len(self.text)}")
        for span in self.spans:
            if self.text[span.start : span.end] != span.text:
                raise ValueError(
                    f"{self.block_id}: span text {span.text!r} differs from text[{span.start}:{span.end}]"
                )
        return self


class Page(Strict):
    volume: int
    n: int
    scan_page: int
    source_key: str
    source_url: str | None
    block_ids: list[str]
    raw_extras: dict[str, Any] = {}


class TocEntry(Strict):
    index: int
    title: str
    source_page_key: str
    depth: int


class SourceMetadata(Strict):
    """Bibliographic data exactly as the source states it (not yet validated)."""

    title_as_source: str | None
    author_as_source: str | None
    author_name: str | None
    author_death_hijri: int | None
    editor: str | None
    publisher: str | None
    edition: str | None
    year_hijri: int | None
    year_gregorian: int | None
    category_id: str | None
    category_name: str | None
    claimed_page_count: int | None
    page_numbering: str | None
    card: list[dict[str, str]] = []
    toc: list[TocEntry] = []


class SourceQuality(Strict):
    status: str | None
    passed: bool | None
    claimed_pages: int | None
    held_pages: int | None
    short_pct: float | None
    tolerance: str | None
    archive_code: str | None


class CanonicalBook(Strict):
    canonical_schema_version: Literal["1.0"] = CANONICAL_SCHEMA_VERSION
    book: BookRef
    source: SourceInfo
    metadata: SourceMetadata
    quality: SourceQuality | None
    scan: dict[str, Any]
    pages: list[Page]
    blocks: dict[str, Block]  # keyed by block_id; insertion order = reading order
    raw_extras: dict[str, Any] = {}
    canonical_content_hash: str = Field(pattern=SHA256_PATTERN)

    _page_index: dict[tuple[int, int], Page] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        for key, block in self.blocks.items():
            if key != block.block_id:
                raise ValueError(f"blocks key {key!r} differs from block_id {block.block_id!r}")
        orders = [block.order for block in self.blocks.values()]
        if orders != list(range(len(orders))):
            raise ValueError("block order must be 0..N-1 in reading (insertion) order")
        seen: set[tuple[int, int]] = set()
        for page in self.pages:
            missing = [block_id for block_id in page.block_ids if block_id not in self.blocks]
            if missing:
                raise ValueError(f"page {page.n} lists unknown blocks: {', '.join(missing)}")
            if (page.volume, page.n) in seen:
                raise ValueError(f"duplicate page {page.n} in volume {page.volume}")
            seen.add((page.volume, page.n))
        return self

    def model_post_init(self, context: Any, /) -> None:
        self._page_index = {(page.volume, page.n): page for page in self.pages}

    def block(self, block_id: str) -> Block:
        """Block by source ID; raises `KeyError` if absent."""
        try:
            return self.blocks[block_id]
        except KeyError:
            raise KeyError(f"unknown block {block_id!r}") from None

    def blocks_in_order(self) -> list[Block]:
        """All blocks in global reading order."""
        return sorted(self.blocks.values(), key=lambda block: block.order)

    def page(self, n: int, volume: int = 1) -> Page:
        """Page by printed number; raises `KeyError` if the book does not hold it."""
        try:
            return self._page_index[(volume, n)]
        except KeyError:
            raise KeyError(f"page {n} (volume {volume}) not in book") from None
