---
id: T-050
title: "Footnote reference resolution"
epic: E05
priority: P0
depends_on: [T-012, T-034]
estimate: S
owner: agent
status: done
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
- [x] 300 annotations, 300 resolved, 0 broken.
- [x] 59 refs start at offset 0; 74 entry-level footnotes (marker like '٨ -').
- [x] b000018 ref 38–41 → b000020.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_refs.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- Contract `Annotation` fields: the source span is `marker_anchor`, the target `target_block_ids` (T-051 appends continuation blocks), `link_method = source_ref`, `status` verified / candidate / unlinked. The ticket's `entry_footnote` classification is the contract's `is_entry_note` (target marker "N -"); 59 of those refs start at offset 0, the other entry refs sit mid-block (several entries per block), 74 distinct entry-note footnotes in total.
- Checks: target missing or not a footnote → `unlinked`, empty targets, `broken_ref`; ref span text ≠ target marker (after stripping brackets) → `candidate` + `broken_ref` warning (EC-045). The sample has none.
- Annotation IDs: `ann` + `source_block|start|target_block` (ADR-011). `annotations.json` = `{annotations: [...]}`.
