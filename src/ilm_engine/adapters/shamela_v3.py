"""Adapter for the archive's Shamela export, `af_schema` 3.0 (`source_code="src-shamela"`).

Maps the source JSON onto the canonical book (03-data-contracts §2). Text, markers, refs and span
classes are copied verbatim; nothing is normalized or interpreted here. The input dict is only read.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ilm_engine.adapters.registry import AdapterError, register
from ilm_engine.canonical.models import (
    Block,
    BookRef,
    CanonicalBook,
    Page,
    Ref,
    SourceInfo,
    SourceMetadata,
    SourceQuality,
    Span,
    TocEntry,
)
from ilm_engine.integrity.hashing import block_hash, content_hash
from ilm_engine.nlp.arabic_digits import to_int

_PDF_PAGE = re.compile(rb"/Type\s*/Page(?![a-zA-Z])")


class SourceFormatError(AdapterError):
    """A required field is missing or malformed (issue `schema_invalid`; the book is not processed)."""


def _get(raw: Any, path: str, required: bool = True) -> Any:
    value = raw
    for part in path.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            if required:
                raise SourceFormatError(f"missing required field {path!r}")
            return None
    return value


def _str_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def _int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return to_int(str(value))
    except ValueError:
        return None


def pdf_page_count(path: Path) -> int | None:
    """Number of page objects in a PDF, without parsing it (the scan has no text layer)."""
    try:
        count = len(_PDF_PAGE.findall(path.read_bytes()))
    except OSError:
        return None
    return count or None


class ShamelaV3Adapter:
    adapter_id = "shamela_v3"
    source_code = "src-shamela"
    schema_versions = frozenset({"3.0"})
    adapter_version = "1.0.0"

    def detect(self, raw: dict[str, Any]) -> bool:
        pages = _get(raw, "content.pages", required=False)
        return _get(raw, "pub.source_code", required=False) == self.source_code and isinstance(pages, list)

    def to_canonical(self, raw: dict[str, Any], pdf_path: Path | None = None) -> CanonicalBook:
        pub_id = str(_get(raw, "pub.id"))
        revision = _get(raw, "revision.r")
        if not isinstance(revision, int):
            raise SourceFormatError("field 'revision.r' must be an integer")
        pub_ref = f"{pub_id}@r{revision}"

        pages, blocks = self._pages_and_blocks(raw)
        return CanonicalBook(
            book=BookRef(
                pub_id=pub_id,
                revision=revision,
                pub_ref=pub_ref,
                source_work_id=_str_or_none(_get(raw, "pub.work_id", False) or _get(raw, "work.id", False)),
                edition_id=_str_or_none(_get(raw, "pub.edition_ref", False)),
            ),
            source=SourceInfo(
                source_code=str(_get(raw, "pub.source_code")),
                source_book_key=str(_get(raw, "pub.source_book_key")),
                schema_version=str(_get(raw, "metadata.af_schema")),
                source_adapter_semver=_str_or_none(_get(raw, "revision.adapter_semver", False)),
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                claim_type=_str_or_none(_get(raw, "pub.claim_type", False)),
                source_declared_hash=_str_or_none(_get(raw, "content.content_sha256", False)),
                source_declared_hash_verified=False,
            ),
            metadata=self._metadata(raw),
            quality=self._quality(raw),
            scan=self._scan(raw, pdf_path),
            pages=pages,
            blocks={block.block_id: block for block in blocks},
            canonical_content_hash=content_hash(blocks),
        )

    def _pages_and_blocks(self, raw: dict[str, Any]) -> tuple[list[Page], list[Block]]:
        source_pages = _get(raw, "content.pages")
        if not isinstance(source_pages, list):
            raise SourceFormatError("field 'content.pages' must be a list")
        pages: list[Page] = []
        blocks: list[Block] = []
        for page_index, source_page in enumerate(source_pages):
            where = f"content.pages.{page_index}"
            n, volume = _get(source_page, "n"), _get(source_page, "volume", False) or 1
            block_ids = []
            for block_index, source_block in enumerate(_get(source_page, "blocks") or []):
                text = _get(source_block, "text")
                if not isinstance(text, str):
                    raise SourceFormatError(f"{where}.blocks.{block_index}.text must be a string")
                block = Block(
                    block_id=str(_get(source_block, "b")),
                    order=len(blocks),
                    page=n,
                    volume=volume,
                    kind=_get(source_block, "kind"),
                    text=text,
                    marker=_str_or_none(source_block.get("marker")),
                    continues=bool(source_block.get("continues", False)),
                    refs=[
                        Ref(start=r["start"], end=r["end"], to=r["to"])
                        for r in source_block.get("refs") or []
                    ],
                    spans=[
                        Span.model_validate({key: s[key] for key in ("class", "start", "end", "text")})
                        for s in source_block.get("spans") or []
                    ],
                    block_hash=block_hash(text),
                )
                blocks.append(block)
                block_ids.append(block.block_id)
            pages.append(
                Page(
                    volume=volume,
                    n=n,
                    scan_page=_get(source_page, "scan_page"),
                    source_key=str(_get(source_page, "source_ref.key")),
                    source_url=_str_or_none(_get(source_page, "source_ref.url", False)),
                    block_ids=block_ids,
                )
            )
        return pages, blocks

    def _metadata(self, raw: dict[str, Any]) -> SourceMetadata:
        attributes = _get(raw, "metadata.source_attributes", False) or {}
        edition = _get(raw, "editions.0", False) or {}
        toc = [
            TocEntry(
                index=i, title=entry["title"], source_page_key=str(entry["source_page"]), depth=entry["depth"]
            )
            for i, entry in enumerate(attributes.get("toc") or [])
        ]
        card = [
            {
                "label": str(row.get("label", "")),
                "value": str(row.get("value", "")),
                "group": str(row.get("group", "")),
            }
            for row in attributes.get("card") or []
        ]
        return SourceMetadata(
            title_as_source=_str_or_none(
                _get(raw, "metadata.identity.title_as_source", False)
                or _get(raw, "pub.title_as_source", False)
            ),
            author_as_source=_str_or_none(
                _get(raw, "metadata.identity.author_as_source", False)
                or _get(raw, "pub.author_as_source", False)
            ),
            author_name=_str_or_none(_get(attributes, "author.name", False)),
            author_death_hijri=_int_or_none(_get(attributes, "author.death.hijri", False)),
            editor=_str_or_none(attributes.get("editor")),
            publisher=_str_or_none(attributes.get("publisher") or edition.get("publisher")),
            edition=_str_or_none(attributes.get("edition")),
            year_hijri=_int_or_none(edition.get("year_hijri")),
            year_gregorian=_int_or_none(edition.get("year_gregorian") or edition.get("year")),
            category_id=_str_or_none(
                _get(raw, "pub.category.id", False) or attributes.get("source_category_id")
            ),
            category_name=_str_or_none(_get(raw, "pub.category.name", False)),
            claimed_page_count=_int_or_none(attributes.get("page_count")),
            page_numbering=_str_or_none(attributes.get("page_numbering")),
            card=card,
            toc=toc,
        )

    def _quality(self, raw: dict[str, Any]) -> SourceQuality | None:
        quality = raw.get("quality")
        if not isinstance(quality, dict):
            return None
        detail = _get(quality, "auto.detail", False) or {}
        return SourceQuality(
            status=_str_or_none(quality.get("status")),
            passed=_get(quality, "auto.passed", False),
            claimed_pages=_int_or_none(detail.get("claimed")),
            held_pages=_int_or_none(detail.get("held")),
            short_pct=detail.get("short_pct"),
            tolerance=_str_or_none(detail.get("tolerance")),
            archive_code=_str_or_none(_get(quality, "auto.archive_code", False)),
        )

    def _scan(self, raw: dict[str, Any], pdf_path: Path | None) -> dict[str, Any]:
        scan = _get(raw, "_meta.scan", False) or {}
        return {
            "available": bool(scan.get("available", pdf_path is not None)),
            "volumes": list(scan.get("volumes") or []),
            "file": pdf_path.name if pdf_path is not None else scan.get("saved_file"),
            "page_count": pdf_page_count(pdf_path) if pdf_path is not None else None,
        }


register(ShamelaV3Adapter())
