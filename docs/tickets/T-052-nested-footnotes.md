---
id: T-052
title: "Nested footnotes and unlinked footnotes"
epic: E05
priority: P1
depends_on: [T-050]
estimate: S
owner: agent
status: todo
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
- [ ] Exactly 1 candidate: b000215, linked to b000210 at the '(أ)' offset.
- [ ] 0 remaining `unlinked_footnote` on the sample.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_nested.py -q
```

## Out of scope
- Anything not listed in Scope.
