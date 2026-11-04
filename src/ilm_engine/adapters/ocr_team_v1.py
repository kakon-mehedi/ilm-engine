"""Adapter for the (hypothetical) in-house OCR team format, version 1.x (`source_code="src-ocr-team"`).

The format has pages of recognized lines with bounding boxes, footnotes as a separate list per page,
and no footnote references; marker linking is left to the annotation step (`unlinked_footnote`).
Bounding boxes stay in `raw_extras` until a canonical field is approved (EC-005). The input declares
no `pub.source_code` / `metadata.af_schema`, so the registry finds this adapter through `detect()`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ilm_engine.adapters.registry import register
from ilm_engine.adapters.shamela_v3 import SourceFormatError, pdf_page_count
from ilm_engine.canonical.models import (
    Block,
    BookRef,
    CanonicalBook,
    Page,
    SourceInfo,
    SourceMetadata,
)
from ilm_engine.integrity.hashing import block_hash, content_hash

_LINE_KEYS = {"id", "role", "text"}
_FOOTNOTE_KEYS = {"id", "marker", "text"}


class OcrTeamV1Adapter:
    adapter_id = "ocr_team_v1"
    source_code = "src-ocr-team"
    schema_versions = frozenset({"1.0"})
    adapter_version = "1.0.0"

    def detect(self, raw: dict[str, Any]) -> bool:
        return raw.get("format") == "ocr-team" and str(raw.get("version", "")).split(".")[0] == "1"

    def to_canonical(self, raw: dict[str, Any], pdf_path: Path | None = None) -> CanonicalBook:
        document = raw.get("document")
        if not isinstance(document, dict) or "id" not in document or not isinstance(raw.get("pages"), list):
            raise SourceFormatError("ocr-team input needs 'document.id' and a 'pages' list")
        revision = int(document.get("revision", 1))
        pub_ref = f"{document['id']}@r{revision}"

        pages: list[Page] = []
        blocks: list[Block] = []
        for page in raw["pages"]:
            n = int(page["page_no"])
            ids = []
            items = [
                (line, "heading" if line.get("role") == "heading" else "text", _LINE_KEYS)
                for line in page["lines"]
            ]
            items += [(note, "footnote", _FOOTNOTE_KEYS) for note in page.get("footnotes", [])]
            for item, kind, known in items:
                text = item["text"]
                blocks.append(
                    Block(
                        block_id=str(item["id"]),
                        order=len(blocks),
                        page=n,
                        volume=1,
                        kind=kind,  # type: ignore[arg-type]
                        text=text,
                        marker=item.get("marker"),
                        block_hash=block_hash(text),
                        raw_extras={key: value for key, value in item.items() if key not in known},
                    )
                )
                ids.append(str(item["id"]))
            pages.append(
                Page(
                    volume=1,
                    n=n,
                    scan_page=int(page.get("image_page", n)),
                    source_key=str(n),
                    source_url=None,
                    block_ids=ids,
                )
            )

        return CanonicalBook(
            book=BookRef(
                pub_id=str(document["id"]),
                revision=revision,
                pub_ref=pub_ref,
                source_work_id=None,
                edition_id=None,
            ),
            source=SourceInfo(
                source_code=self.source_code,
                source_book_key=str(document["id"]),
                schema_version=str(raw.get("version")),
                source_adapter_semver=None,
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                claim_type=None,
                source_declared_hash=None,
            ),
            metadata=SourceMetadata(
                title_as_source=document.get("title"),
                author_as_source=document.get("author"),
                author_name=document.get("author"),
                author_death_hijri=None,
                editor=document.get("editor"),
                publisher=None,
                edition=None,
                year_hijri=None,
                year_gregorian=None,
                category_id=None,
                category_name=document.get("category"),
                claimed_page_count=document.get("page_count"),
                page_numbering=None,
            ),
            quality=None,
            scan={
                "available": pdf_path is not None,
                "volumes": [1],
                "file": pdf_path.name if pdf_path else None,
                "page_count": pdf_page_count(pdf_path) if pdf_path else None,
            },
            pages=pages,
            blocks={block.block_id: block for block in blocks},
            raw_extras={
                "top": {key: value for key, value in raw.items() if key not in ("pages",)},
                "blocks": {block.block_id: dict(block.raw_extras) for block in blocks if block.raw_extras},
            },
            canonical_content_hash=content_hash(blocks),
        )


register(OcrTeamV1Adapter())
