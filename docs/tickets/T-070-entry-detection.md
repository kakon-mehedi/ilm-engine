---
id: T-070
title: "Biographical entry detection (75 entries)"
epic: E07
priority: P0
depends_on: [T-034, T-061]
estimate: M
owner: agent
status: todo
wave: 6
---

# T-070 — Biographical entry detection (75 entries)

**Epic:** E07 Knowledge units · **Priority:** P0 · **Estimate:** M · **Wave:** 6

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement C/F: segment the author's text into knowledge units. Entries can share a block ('١٨ - حمزة. … ١٩ - والعباس.') or start mid-sentence ('وأختهم: ٣٢ - أروى').

## Scope
- Scan `author_text` blocks from `entries.start_page` (21) with regex `(?<![٠-٩(/])([٠-٩]+) ?- `; each match starts an entry that ends before the next match or block end.
- Entry may continue into the next block if it has no next match and next block is author_text without heading (join as multi-anchor).
- Checks: sequence 1..N → issue `numbering_gap` / `numbering_duplicate`; before flagging a gap, re-scan with a looser fallback regex (lesson: naive regex falsely missed #32).

## Files
- `src/ilm_engine/extractors/units.py`
- `tests/test_entries.py`

## Implementation notes
- Editor's numbered lists on pages 6–12 must not be counted (origin filter).

## Acceptance criteria
- [ ] Exactly 75 entries numbered 1..75, no gaps, no duplicates.
- [ ] #32 found in b000294 with anchor quote starting '٣٢ - أروى'.
- [ ] #18 and #19 both in b000217; #8 = b000135 [0:102].
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_entries.py -q
```

## Out of scope
- Anything not listed in Scope.
