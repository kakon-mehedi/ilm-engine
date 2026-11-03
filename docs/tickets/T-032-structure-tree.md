---
id: T-032
title: "Structure tree from headings"
epic: E03
priority: P0
depends_on: [T-012, T-003]
estimate: M
owner: agent
status: todo
wave: 4
---

# T-032 — Structure tree from headings

**Epic:** E03 Document analysis, structure, origin · **Priority:** P0 · **Estimate:** M · **Wave:** 4

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement C: identify volumes, chapters, sections.

## Scope
- Build `Section{id, title, level, heading_block_id, start_block_id, end_block_id, start_page, end_page, children}` from `toc_heading` + `heading` blocks in order.
- Level: `toc_heading`=1; `heading` level from matched TOC depth (T-033) else 2.
- Root = book; volume 1 node.
- Write `structure.json`.

## Files
- `src/ilm_engine/processors/structure.py`
- `tests/test_structure.py`

## Implementation notes
- Headings starting with '*' are section headings of the author's text.

## Acceptance criteria
- [ ] 17 section nodes (15 heading + 2 toc_heading).
- [ ] First section 'مقدمة المحقق' starts at b000012 (p.5); 'مقدمة المؤلف' at b000090 (p.19).
- [ ] Every block belongs to exactly one deepest section.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_structure.py -q
```

## Out of scope
- Anything not listed in Scope.
