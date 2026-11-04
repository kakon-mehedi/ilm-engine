---
id: T-033
title: "TOC alignment via source_ref.key"
epic: E03
priority: P0
depends_on: [T-032]
estimate: S
owner: agent
status: done
wave: 5
---

# T-033 — TOC alignment via source_ref.key

**Epic:** E03 Document analysis, structure, origin · **Priority:** P0 · **Estimate:** S · **Wave:** 5

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
TOC `source_page` is the Shamela key, not the printed page `n`; the offset varies (2 → 3 → 4).

## Scope
- Match each TOC entry to a heading by `page.source_key == toc.source_page` + normalized title similarity.
- Record `printed_page` (n) and `offset = n - int(source_page)`.
- Issues: `toc_without_block` (TOC entry placed as toc_heading by source — 2 cases from `source_extras`), `heading_without_toc`, `toc_page_offset` (info).

## Files
- `src/ilm_engine/processors/structure.py`
- `tests/test_toc_alignment.py`

## Implementation notes
- Use `nlp/normalize.py` for title comparison (T-060).

## Acceptance criteria
- [x] All 17 TOC entries matched.
- [x] 'مقدمة المؤلف' TOC source_page 15 → printed page 19.
- [x] Offsets observed are {2, 3, 4}.
- [x] 2 `toc_without_block` info issues (pages 5 and 19).
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_toc_alignment.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- Matching: same source page key, then normalized title similarity (footnote markers, '*', brackets and punctuation removed; containment = 1.0, else difflib ratio ≥ 0.6). All 17 entries match.
- **Offsets, reported precisely:** over all pages the key→n offset takes the values {2, 3, 4} (`structure.page_offsets`, as DECISIONS §7 states); the 17 TOC entries themselves only show {3, 4}. `toc_page_offset` (info) lists the TOC offsets per entry.
- `toc_without_block` (info) for the two entries the source placed as toc_heading blocks (pages 5 and 19); an entry matching nothing would be a warning. No `heading_without_toc` on the sample.
- `structure.json` gains `toc_alignment` (one row per TOC entry: printed page, offset, heading block, similarity) and `page_offsets`.
