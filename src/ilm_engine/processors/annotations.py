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
    continuation_of: dict[str, str] = field(default_factory=dict)  # continued block → previous footnote block

    def by_target(self) -> dict[str, list[Annotation]]:
        index: dict[str, list[Annotation]] = {}
        for annotation in self.annotations:
            for block_id in annotation.target_block_ids:
                index.setdefault(block_id, []).append(annotation)
        return index

    def to_json(self) -> dict[str, Any]:
        return {"annotations": self.annotations, "continuations": self.continuation_of}


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


def join_continuations(book: CanonicalBook, result: Annotations) -> Annotations:
    """Join each `continues` footnote to the footnote it continues on the previous existing page (T-051):
    the one ending with the continuation mark "=", else the page's last footnote.

    The logical footnote becomes one annotation whose `target_block_ids` list every part in order;
    the original blocks are untouched.
    """
    ctx = _Context(book)
    pages = book.pages
    footnotes_on = {
        (page.volume, page.n): [b for b in page.block_ids if book.block(b).kind == "footnote"]
        for page in pages
    }
    previous_page = {
        (pages[i].volume, pages[i].n): (pages[i - 1].volume, pages[i - 1].n) for i in range(1, len(pages))
    }

    continuation_of: dict[str, str] = {}
    issues: list[Issue] = []
    for block in book.blocks_in_order():
        if block.kind != "footnote" or not block.continues:
            continue
        before = previous_page.get((block.volume, block.page))
        candidates = footnotes_on.get(before, []) if before else []
        if not candidates:
            issues.append(
                make_issue(
                    ctx.pub_ref,
                    "unlinked_footnote",
                    "warning",
                    "annotation",
                    block.block_id,
                    f"Footnote {block.block_id} continues from a previous page that has no footnote.",
                    STEP,
                )
            )
            continue
        # The part to continue ends with "=" (EC-040); a nested footnote may be printed after it (p.33).
        marked = [b for b in candidates if book.block(b).text.rstrip().endswith("=")]
        continuation_of[block.block_id] = marked[-1] if marked else candidates[-1]

    def root(block_id: str) -> str:
        while block_id in continuation_of:
            block_id = continuation_of[block_id]
        return block_id

    chains: dict[str, list[str]] = {}
    for block_id in continuation_of:  # reading order, so parts are appended in order
        chains.setdefault(root(block_id), []).append(block_id)

    updated = []
    for annotation in result.annotations:
        first = annotation.target_block_ids[0] if annotation.target_block_ids else None
        if first in chains:
            annotation = annotation.model_copy(update={"target_block_ids": [first, *chains[first]]})
        updated.append(annotation)
    for start, parts in chains.items():
        for part in parts:
            issues.append(
                make_issue(
                    ctx.pub_ref,
                    "continued_footnote_joined",
                    "info",
                    "annotation",
                    part,
                    f"Footnote {part} (page {book.block(part).page}) continues {continuation_of[part]}; "
                    f"joined into one note starting at {start}.",
                    STEP,
                    details={"continuation_of": continuation_of[part], "first_part": start},
                )
            )
    return Annotations(updated, [*result.issues, *issues], continuation_of)


def link_nested(book: CanonicalBook, result: Annotations) -> Annotations:
    """Footnotes no ref points to (and not continuation parts) are looked up as "(marker)" inside the
    other footnotes of their page: a single match is a nested footnote (EC-042); otherwise the
    footnote is `unlinked_footnote` and goes to review (EC-043)."""
    ctx = _Context(book)
    targeted = set(result.by_target())
    added: list[Annotation] = []
    issues: list[Issue] = []
    for block in book.blocks_in_order():
        if block.kind != "footnote" or block.block_id in targeted or block.block_id in result.continuation_of:
            continue
        hits: list[tuple[Block, int]] = []
        if block.marker:
            needle = f"({block.marker.strip()})"
            for other_id in book.page(block.page, block.volume).block_ids:
                other = book.block(other_id)
                if other.kind == "footnote" and other_id != block.block_id:
                    hits += [(other, match.start()) for match in re.finditer(re.escape(needle), other.text)]
        if not hits:
            issues.append(
                make_issue(
                    ctx.pub_ref,
                    "unlinked_footnote",
                    "warning",
                    "annotation",
                    block.block_id,
                    f"Footnote {block.block_id} (p.{block.page}, marker {block.marker!r}) is not referenced.",
                    STEP,
                    details={"marker": block.marker},
                )
            )
            continue
        parent, start = hits[0]
        end = start + len(f"({block.marker.strip()})")  # type: ignore[union-attr]
        status = "verified" if len(hits) == 1 else "candidate"
        added.append(
            Annotation(
                annotation_id=make_id(
                    "ann", ctx.pub_ref, natural_key(parent.block_id, start, block.block_id)
                ),
                type="nested_footnote",
                source_block_id=parent.block_id,
                marker_anchor=ctx.anchor(parent, start, end),
                target_block_ids=[block.block_id],
                marker_text=block.marker,
                link_method="marker_match",
                is_entry_note=False,
                status=status,  # type: ignore[arg-type]
                provenance=Provenance(method="rule", step=STEP, step_version="1.0.0"),
            )
        )
        issues.append(
            make_issue(
                ctx.pub_ref,
                "nested_footnote",
                "warning",
                "annotation",
                block.block_id,
                f"Footnote with marker {block.marker!r} has no incoming ref; matched to "
                f"{parent.block_id} [{start}:{end}]"
                + ("" if status == "verified" else f" ({len(hits)} candidates)")
                + ".",
                STEP,
                details={
                    "parent_footnote": parent.block_id,
                    "parent_start": start,
                    "parent_end": end,
                    "candidates": len(hits),
                },
            )
        )
    return Annotations([*result.annotations, *added], [*result.issues, *issues], result.continuation_of)


def build(book: CanonicalBook) -> Annotations:
    """All annotation passes of the step: source refs, continued footnotes, nested footnotes."""
    return link_nested(book, join_continuations(book, resolve_refs(book)))
