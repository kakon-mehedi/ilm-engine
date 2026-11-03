---
id: T-143
title: "End-to-end integration test + determinism"
epic: E14
priority: P0
depends_on: [T-142, T-112]
estimate: S
owner: agent
status: todo
wave: 12
---

# T-143 — End-to-end integration test + determinism

**Epic:** E14 Pipeline runner & CLI · **Priority:** P0 · **Estimate:** S · **Wave:** 12

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Proof that the whole pipeline works and is repeatable.

## Scope
- `tests/test_e2e.py`: run pipeline into tmp dir twice (no cache second time) → all output file hashes identical except run_manifest timestamps/run_id.
- Assert headline numbers: 594 blocks, 75 units, 300/300 refs, 16 continuations, 1 nested footnote, data/ unchanged.

## Files
- `tests/test_e2e.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Test passes; failure messages name the differing file.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_e2e.py -q
```

## Out of scope
- Anything not listed in Scope.
