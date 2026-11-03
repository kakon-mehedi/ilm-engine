---
id: T-032
title: "Structure tree from headings"
epic: E03
priority: P0
depends_on: [T-012, T-003]
estimate: M
owner: agent
status: done
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
- [x] 17 section nodes (15 heading + 2 toc_heading).
- [x] First section 'مقدمة المحقق' starts at b000012 (p.5); 'مقدمة المؤلف' at b000090 (p.19).
- [x] Every block belongs to exactly one deepest section.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_structure.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- 17 sections (15 heading + 2 toc_heading) plus one root section for the book (level 0); `structure.json` = `{root_section_id, sections}` (03-data-contracts §18). The sample has one volume, so no separate volume node is created; the root stands for the book/volume 1.
- Levels: `toc_heading` → 1; `heading` → depth of the TOC entry on the same source page, else 2 (12 level-1, 5 level-2 on the sample). T-033 adds title verification, printed page offsets and alignment issues.
- Section IDs: `sec` + `toc_index|heading_block_id` (ADR-011); root: `root|<first block>`.
- `Section.origin` is provisional at this step (editor_text before "مقدمة المؤلف", author_text after) because the origin step runs later; T-034 assigns per-block origins.
- Blocks before the first heading (title page b000001–b000011) belong to the root section.
