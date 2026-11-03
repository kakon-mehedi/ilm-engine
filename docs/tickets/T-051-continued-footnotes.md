---
id: T-051
title: "Join footnotes continued across pages"
epic: E05
priority: P0
depends_on: [T-050]
estimate: S
owner: agent
status: todo
wave: 7
---

# T-051 — Join footnotes continued across pages

**Epic:** E05 Annotations, citations, related works · **Priority:** P0 · **Estimate:** S · **Wave:** 7

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
A footnote can continue on the next page (`continues: true`, text starts with '=', no marker).

## Scope
- Link each continued block to the previous footnote (last footnote of previous page) as `continuation_of`.
- Logical footnote = ordered list of block anchors (originals untouched).
- Issue `continued_footnote_joined` (info) for each.

## Files
- `src/ilm_engine/processors/annotations.py`
- `tests/test_continued.py`

## Implementation notes
- Previous page = previous existing page in order (pages may be missing).

## Acceptance criteria
- [ ] 16 continuation links; b000103 (p.20) joins the last footnote of p.19 (b000097).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_continued.py -q
```

## Out of scope
- Anything not listed in Scope.
