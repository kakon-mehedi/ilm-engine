---
id: T-033
title: "TOC alignment via source_ref.key"
epic: E03
priority: P0
depends_on: [T-032]
estimate: S
owner: agent
status: todo
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
- [ ] All 17 TOC entries matched.
- [ ] 'مقدمة المؤلف' TOC source_page 15 → printed page 19.
- [ ] Offsets observed are {2, 3, 4}.
- [ ] 2 `toc_without_block` info issues (pages 5 and 19).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_toc_alignment.py -q
```

## Out of scope
- Anything not listed in Scope.
