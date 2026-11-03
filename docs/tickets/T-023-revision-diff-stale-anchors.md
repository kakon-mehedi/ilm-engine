---
id: T-023
title: "Revision diff + stale anchor detection"
epic: E02
priority: P1
depends_on: [T-020, T-110]
estimate: M
owner: agent
status: todo
wave: 3
---

# T-023 — Revision diff + stale anchor detection

**Epic:** E02 Integrity · **Priority:** P1 · **Estimate:** M · **Wave:** 3

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
When r6 becomes r7, unchanged blocks keep their enrichment; changed blocks are re-processed and their anchors marked stale.

## Scope
- `integrity/revision_diff.py`: `diff(old_book, new_book) -> {unchanged, changed, added, removed}` by block_id + block_hash.
- Mark anchors on changed/removed blocks `stale=True` + issue `anchor_stale`.
- Return the set of block IDs to re-process (incremental run).

## Files
- `src/ilm_engine/integrity/revision_diff.py`
- `tests/test_revision_diff.py`

## Implementation notes
- Simulate r7 in tests by editing one block text in a copy.

## Acceptance criteria
- [ ] Editing `b000135` text in a simulated r7 → diff reports exactly 1 changed block; all anchors on b000135 become stale; others untouched.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_revision_diff.py -q
```

## Out of scope
- Anything not listed in Scope.
