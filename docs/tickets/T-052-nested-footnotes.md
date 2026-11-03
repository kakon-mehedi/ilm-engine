---
id: T-052
title: "Nested footnotes and unlinked footnotes"
epic: E05
priority: P1
depends_on: [T-050]
estimate: S
owner: agent
status: done
wave: 7
---

# T-052 — Nested footnotes and unlinked footnotes

**Epic:** E05 Annotations, citations, related works · **Priority:** P1 · **Estimate:** S · **Wave:** 7

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
JSON has 0 refs from footnotes. b000215 (p.33, marker 'أ') is the note of '(أ)' inside footnote b000210.

## Scope
- Find footnotes not targeted by any ref and not continuations → candidates.
- Search same-page footnotes for '(<marker>)' → create annotation with `type:'nested_footnote'`, confidence rule-based, issue `nested_footnote`.
- Still unlinked → `unlinked_footnote` → review queue.

## Files
- `src/ilm_engine/processors/annotations.py`
- `tests/test_nested.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] Exactly 1 candidate: b000215, linked to b000210 at the '(أ)' offset.
- [x] 0 remaining `unlinked_footnote` on the sample.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_nested.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- Candidates are footnotes targeted by no annotation and not continuation parts: exactly one on the sample, b000215. It links to "(أ)" at b000210 [30:33] as a `nested_footnote` annotation (`link_method: marker_match`, rule provenance, status `verified` for a single match, `candidate` for several), with issue `nested_footnote` (warning, as in 03-data-contracts §4).
- A footnote that stays unreferenced raises `unlinked_footnote` (none on the sample). With the 300 ref annotations this gives 301 annotations covering all 317 footnotes (16 as continuation parts).
