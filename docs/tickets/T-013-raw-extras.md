---
id: T-013
title: "Preserve unknown fields (raw_extras)"
epic: E01
priority: P1
depends_on: [T-012]
estimate: S
owner: agent
status: todo
wave: 4
---

# T-013 — Preserve unknown fields (raw_extras)

**Epic:** E01 Canonical model + adapters · **Priority:** P1 · **Estimate:** S · **Wave:** 4

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
If the source JSON gains new fields, we must not silently lose them.

## Scope
- Adapter collects every top-level key and per-block key it does not map into `raw_extras` (`{'top': {...}, 'blocks': {block_id: {...}}}`).
- `_meta`, `quality`, `timeline` go into `raw_extras.top` verbatim.
- Warn-level log listing unmapped keys.

## Files
- `src/ilm_engine/adapters/shamela_v3.py`
- `tests/test_raw_extras.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Adding `"foo": 1` to a block in a test copy ends up in `raw_extras.blocks[<id>].foo`.
- [ ] `raw_extras.top.quality.auto.detail.claimed == 72`.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_raw_extras.py -q
```

## Out of scope
- Anything not listed in Scope.
