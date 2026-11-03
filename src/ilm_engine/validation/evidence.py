"""Evidence guard (ADR-007): a quote is evidence only if it exists in the cited original block.

`locate` searches the original block text for the quote:
- exact match → evidence factor 1.0;
- match only after normalization (ADR-012) → factor 0.9, offsets mapped back to the original text;
- no match → None (factor 0): the caller rejects the item with issue `evidence_not_found`.
If the quote occurs several times, the occurrence nearest to `hint_start` is used; without a hint the
first one is used and `ambiguity_penalty` is 0.9.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ilm_engine.canonical.models import Block
from ilm_engine.enrichment.models import Anchor
from ilm_engine.nlp.normalize import normalize, normalize_with_map

EXACT_FACTOR = 1.0
NORMALIZED_FACTOR = 0.9
AMBIGUITY_PENALTY = 0.9


@dataclass(frozen=True)
class EvidenceMatch:
    anchor: Anchor
    match: Literal["exact", "normalized"]
    factor: float  # evidence factor of the confidence formula (DECISIONS §8)
    occurrences: int
    ambiguity_penalty: float = 1.0  # 0.9 when several occurrences and no hint


def locate(
    quote: str,
    block: Block,
    *,
    pub_ref: str,
    scan_page: int,
    hint_start: int | None = None,
) -> EvidenceMatch | None:
    """Find `quote` in `block.text`; None if it is not there even after normalization."""
    if not quote.strip():
        return None

    spans = _exact_spans(block.text, quote)
    match: Literal["exact", "normalized"] = "exact"
    if not spans:
        spans = _normalized_spans(block.text, quote)
        match = "normalized"
    if not spans:
        return None

    if hint_start is not None:
        start, end = min(spans, key=lambda span: (abs(span[0] - hint_start), span[0]))
    else:
        start, end = spans[0]
    anchor = Anchor(
        pub_ref=pub_ref,
        page=block.page,
        scan_page=scan_page,
        block_id=block.block_id,
        start=start,
        end=end,
        quote=block.text[start:end],
        block_hash=block.block_hash,
    )
    return EvidenceMatch(
        anchor=anchor,
        match=match,
        factor=EXACT_FACTOR if match == "exact" else NORMALIZED_FACTOR,
        occurrences=len(spans),
        ambiguity_penalty=AMBIGUITY_PENALTY if len(spans) > 1 and hint_start is None else 1.0,
    )


def anchor_status(anchor: Anchor, block: Block | None) -> Literal["valid", "stale", "orphaned"]:
    """`valid` if the anchor still points at its quote in an unchanged block (ADR-017)."""
    if block is None:
        return "orphaned"
    if block.block_hash != anchor.block_hash or anchor.end > len(block.text):
        return "stale"
    if not anchor.quote_truncated and block.text[anchor.start : anchor.end] != anchor.quote:
        return "stale"
    return "valid"


def _exact_spans(text: str, quote: str) -> list[tuple[int, int]]:
    spans = []
    position = text.find(quote)
    while position != -1:
        spans.append((position, position + len(quote)))
        position = text.find(quote, position + 1)
    return spans


def _normalized_spans(text: str, quote: str) -> list[tuple[int, int]]:
    for profile in ("match", "search"):
        needle = normalize(quote, profile)
        if not needle:
            return []
        haystack = normalize_with_map(text, profile)
        spans = []
        position = haystack.text.find(needle)
        while position != -1:
            spans.append(haystack.to_original(position, position + len(needle)))
            position = haystack.text.find(needle, position + 1)
        if spans:
            return spans
    return []
