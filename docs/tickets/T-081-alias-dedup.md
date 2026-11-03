---
id: T-081
title: "Alias resolution and de-duplication"
epic: E08
priority: P1
depends_on: [T-080]
estimate: M
owner: agent
status: todo
wave: 11
---

# T-081 — Alias resolution and de-duplication

**Epic:** E08 Entities & relationships · **Priority:** P1 · **Estimate:** M · **Wave:** 11

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Same person appears under different surface forms (الدارقطني / أبو الحسن الدارقطني / علي بن عمر الدارقطني).

## Scope
- Merge candidates by normalized (ism + chain prefix ≥2) or nisba+kunya match; produce `aliases`.
- Same ism but conflicting chains → keep separate + issue `ambiguous_entity` (sensitive `narrator_disambiguation` when the person is a narrator).

## Files
- `src/ilm_engine/extractors/entities.py`
- `tests/test_alias.py`

## Implementation notes
- Never merge on ism alone.

## Acceptance criteria
- [ ] Al-Daraqutni mentions (b000004, b000043, card) merge into one entity with ≥3 aliases.
- [ ] Hind #8 and Hind #9 stay separate.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_alias.py -q
```

## Out of scope
- Anything not listed in Scope.
