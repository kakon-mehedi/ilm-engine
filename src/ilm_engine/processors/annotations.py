"""Annotations (step `annotations`, FR-060–FR-061): footnote links of a book.

Every source `Ref` becomes an `Annotation` from the marker span in the text to its footnote block.
The marker span must match the footnote's marker; a ref to a missing or non-footnote block keeps its
source span and raises `broken_ref`. A footnote whose marker is an entry number ("٨ -") is the
biography note of that entry (`is_entry_note`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ilm_engine.canonical.models import Block, CanonicalBook, Ref
from ilm_engine.enrichment.issues import make_issue
from ilm_engine.enrichment.models import Anchor, Annotation, Issue, Provenance
from ilm_engine.ids import make_id, natural_key

STEP = "annotations"
_PROVENANCE = Provenance(method="structural", step=STEP, step_version="1.0.0")
ENTRY_MARKER = re.compile(r"^[٠-٩0-9]+ ?-$")


@dataclass
class Annotations:
    annotations: list[Annotation]
    issues: list[Issue] = field(default_factory=list)

    def by_target(self) -> dict[str, list[Annotation]]:
        index: dict[str, list[Annotation]] = {}
        for annotation in self.annotations:
            for block_id in annotation.target_block_ids:
                index.setdefault(block_id, []).append(annotation)
        return index

    def to_json(self) -> dict[str, Any]:
        return {"annotations": self.annotations}


def marker_key(text: str) -> str:
    """'(١)' / '١' / '٨ -' → comparable marker ('١', '٨ -')."""
    return re.sub(r"\s+", " ", text.strip().strip("()").strip())


def is_entry_marker(marker: str | None) -> bool:
    return bool(marker) and bool(ENTRY_MARKER.match(marker.strip()))  # type: ignore[union-attr]


class _Context:
    def __init__(self, book: CanonicalBook) -> None:
        self.book = book
        self.pub_ref = book.book.pub_ref
        self.scan_pages = {(page.volume, page.n): page.scan_page for page in book.pages}

    def anchor(self, block: Block, start: int, end: int) -> Anchor:
        return Anchor(
            pub_ref=self.pub_ref,
            page=block.page,
            scan_page=self.scan_pages[(block.volume, block.page)],
            block_id=block.block_id,
            start=start,
            end=end,
            quote=block.text[start:end],
            block_hash=block.block_hash,
        )


def _from_ref(ctx: _Context, block: Block, ref: Ref) -> tuple[Annotation, list[Issue]]:
    target = ctx.book.blocks.get(ref.to)
    span = block.text[ref.start : ref.end]
    issues: list[Issue] = []
    status = "verified"
    if target is None or target.kind != "footnote":
        status = "unlinked"
        reason = "does not exist" if target is None else f"is a {target.kind} block, not a footnote"
        issues.append(
            make_issue(
                ctx.pub_ref,
                "broken_ref",
                "warning",
                "block",
                block.block_id,
                f"Ref {span!r} at {ref.start}–{ref.end} points to {ref.to}, which {reason}.",
                STEP,
                details={"to": ref.to, "start": ref.start, "end": ref.end},
                key=f"{ref.start}",
            )
        )
    elif marker_key(span) != marker_key(target.marker or ""):
        status = "candidate"
        issues.append(
            make_issue(
                ctx.pub_ref,
                "broken_ref",
                "warning",
                "block",
                block.block_id,
                f"Ref span {span!r} does not match the marker {target.marker!r} of {ref.to}.",
                STEP,
                details={"to": ref.to, "span": span, "marker": target.marker},
                key=f"{ref.start}",
            )
        )
    marker = target.marker if target is not None else None
    annotation = Annotation(
        annotation_id=make_id("ann", ctx.pub_ref, natural_key(block.block_id, ref.start, ref.to)),
        type="footnote",
        source_block_id=block.block_id,
        marker_anchor=ctx.anchor(block, ref.start, ref.end),
        target_block_ids=[ref.to] if status != "unlinked" else [],
        marker_text=marker,
        link_method="source_ref",
        is_entry_note=is_entry_marker(marker),
        status=status,  # type: ignore[arg-type]
        provenance=_PROVENANCE,
    )
    return annotation, issues


def resolve_refs(book: CanonicalBook) -> Annotations:
    """One annotation per source ref (T-050)."""
    ctx = _Context(book)
    annotations: list[Annotation] = []
    issues: list[Issue] = []
    for block in book.blocks_in_order():
        for ref in block.refs:
            annotation, found = _from_ref(ctx, block, ref)
            annotations.append(annotation)
            issues.extend(found)
    return Annotations(annotations, issues)


def build(book: CanonicalBook) -> Annotations:
    """All annotation passes of the step."""
    return resolve_refs(book)
