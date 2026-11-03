---
id: T-050
title: "Footnote reference resolution"
epic: E05
priority: P0
depends_on: [T-012, T-034]
estimate: S
owner: agent
status: todo
wave: 6
---

# T-050 — Footnote reference resolution

**Epic:** E05 Annotations, citations, related works · **Priority:** P0 · **Estimate:** S · **Wave:** 6

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement E: link annotations to their exact text location.

## Scope
- For every `Ref` create `Annotation{id, type:'footnote', source_anchor (block,start,end,quote), target_block, marker, status}` in `annotations.json`.
- Validate target exists and is a footnote → else `broken_ref`.
- Classify refs at `start == 0` on numbered entries as `entry_footnote` (biography note).

## Files
- `src/ilm_engine/processors/annotations.py`
- `tests/test_refs.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] 300 annotations, 300 resolved, 0 broken.
- [ ] 59 refs start at offset 0; 74 entry-level footnotes (marker like '٨ -').
- [ ] b000018 ref 38–41 → b000020.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_refs.py -q
```

## Out of scope
- Anything not listed in Scope.
