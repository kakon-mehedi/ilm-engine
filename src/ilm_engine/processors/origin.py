"""Origin layers (step `origin`, DECISIONS §6, ADR-010): who said each block.

Rules, then per-book overrides (`config.origin.overrides`, later entries win):
- every footnote block → `editor_footnote` (rule `footnote_kind`; overrides never change footnotes);
- blocks before the author's introduction heading ("مقدمة المؤلف") → `editor_text` (`before_author_intro`);
- blocks of the author's preamble (after that heading, before the first author heading) that open with
  an isnad formula (أخبرنا, حدثنا, …) → `transmission_isnad` (`isnad_formula`);
- all other blocks after the introduction heading → `author_text` (`author_section`).
`ai_generated` is never assigned to a source block.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ilm_engine.canonical.models import Block, CanonicalBook
from ilm_engine.config import Config, OriginOverride
from ilm_engine.enrichment.models import Origin, OriginSpan
from ilm_engine.processors.structure import AUTHOR_INTRO_TITLE

STEP = "origin"
_ISNAD_OPENING = re.compile(r"^\s*(?:أخبرنا|أخبرني|حدثنا|حدثني|أنبأنا|أنبأني)")


@dataclass
class OriginMap:
    blocks: dict[str, Origin]  # block_id → origin, every block exactly once
    rules: dict[str, str]  # block_id → rule that decided it
    spans: list[OriginSpan]
    overrides_applied: list[dict[str, Any]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return dict(sorted(Counter(self.blocks.values()).items()))

    def to_json(self) -> dict[str, Any]:
        return {
            "blocks": self.blocks,
            "spans": self.spans,
            "counts": self.counts(),
            "overrides_applied": self.overrides_applied,
        }


def _in_override(block: Block, override: OriginOverride) -> bool:
    if override.pages is not None:
        return override.pages[0] <= block.page <= override.pages[1]
    assert override.blocks is not None
    return override.blocks[0] <= block.block_id <= override.blocks[1]  # zero-padded ids sort in order


def assign(book: CanonicalBook, config: Config) -> OriginMap:
    blocks = book.blocks_in_order()
    intro = next(
        (
            b.order
            for b in blocks
            if b.kind in ("heading", "toc_heading") and b.text.strip() == AUTHOR_INTRO_TITLE
        ),
        None,
    )
    first_author_heading = next(
        (b.order for b in blocks if intro is not None and b.order > intro and b.kind == "heading"), None
    )

    origins: dict[str, Origin] = {}
    rules: dict[str, str] = {}
    for block in blocks:
        if block.kind == "footnote":
            origins[block.block_id], rules[block.block_id] = "editor_footnote", "footnote_kind"
        elif intro is None or block.order < intro:
            origins[block.block_id], rules[block.block_id] = "editor_text", "before_author_intro"
        elif (first_author_heading is None or block.order < first_author_heading) and _ISNAD_OPENING.match(
            block.text
        ):
            origins[block.block_id], rules[block.block_id] = "transmission_isnad", "isnad_formula"
        else:
            origins[block.block_id], rules[block.block_id] = "author_text", "author_section"

    applied = []
    for index, override in enumerate(config.origin.overrides):
        changed = [
            b.block_id
            for b in blocks
            if b.kind != "footnote" and _in_override(b, override) and origins[b.block_id] != override.origin
        ]
        for block_id in changed:
            origins[block_id], rules[block_id] = override.origin, "override"
        if changed:
            span = (
                {"pages": list(override.pages)} if override.pages else {"blocks": list(override.blocks or ())}
            )
            applied.append(
                {"index": index, **span, "origin": override.origin, "note": override.note, "changed": changed}
            )

    return OriginMap(origins, rules, _spans(blocks, origins, rules), applied)


def _spans(blocks: list[Block], origins: dict[str, Origin], rules: dict[str, str]) -> list[OriginSpan]:
    """Contiguous runs of non-footnote blocks sharing origin and rule (footnotes interleave the text
    on every page, so they are counted, not spanned)."""
    spans: list[OriginSpan] = []
    run: list[Block] = []

    def close() -> None:
        if run:
            first, last = run[0], run[-1]
            spans.append(
                OriginSpan(
                    origin=origins[first.block_id],
                    start_block_id=first.block_id,
                    end_block_id=last.block_id,
                    start_page=first.page,
                    end_page=last.page,
                    rule=rules[first.block_id],
                    block_count=len(run),
                )
            )

    for block in (b for b in blocks if b.kind != "footnote"):
        if run and (origins[block.block_id], rules[block.block_id]) != (
            origins[run[0].block_id],
            rules[run[0].block_id],
        ):
            close()
            run = []
        run.append(block)
    close()
    return spans
