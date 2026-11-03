---
id: T-035
title: "Section → block ranges and page index"
epic: E03
priority: P1
depends_on: [T-032]
estimate: S
owner: agent
status: done
wave: 5
---

# T-035 — Section → block ranges and page index

**Epic:** E03 Document analysis, structure, origin · **Priority:** P1 · **Estimate:** S · **Wave:** 5

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Fast lookup of which section a block/page belongs to (used by units, search and the reader).

## Scope
- `structure.block_section(block_id) -> section_id`, `structure.section_blocks(section_id)`.
- Add `page_index` to `structure.json`: page n → [section ids].

## Files
- `src/ilm_engine/processors/structure.py`
- `tests/test_section_ranges.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] b000135 → section titled '* وأخوة أولاد رسول اللَّه -صلى الله عليه وسلم- من أُمهم خديجة:'.
- [x] Page 25 maps to that section.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_section_ranges.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `Structure.block_section_id(block_id)`, `Structure.section_blocks(section_id, deep=True)` (deep includes subsections; `deep=False` only blocks whose deepest section it is) and `Structure.page_index()`; `structure.json` gains `page_index` (printed page → deepest section IDs, in order of appearance).
- The ticket's title literal is compared after normalization: the source stores the diacritics of "اللَّه" in a different code-point order than the ticket text.
