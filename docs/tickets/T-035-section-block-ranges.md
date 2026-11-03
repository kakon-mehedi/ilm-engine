---
id: T-035
title: "Section → block ranges and page index"
epic: E03
priority: P1
depends_on: [T-032]
estimate: S
owner: agent
status: todo
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
- [ ] b000135 → section titled '* وأخوة أولاد رسول اللَّه -صلى الله عليه وسلم- من أُمهم خديجة:'.
- [ ] Page 25 maps to that section.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_section_ranges.py -q
```

## Out of scope
- Anything not listed in Scope.
