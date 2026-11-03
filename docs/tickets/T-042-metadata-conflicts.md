---
id: T-042
title: "Metadata conflict & variant detection"
epic: E04
priority: P1
depends_on: [T-041]
estimate: S
owner: agent
status: todo
wave: 7
---

# T-042 — Metadata conflict & variant detection

**Epic:** E04 Metadata · **Priority:** P1 · **Estimate:** S · **Wave:** 7

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement A: identify missing or inconsistent metadata.

## Scope
- Compare card vs content values: title spelling variants (الإخوة vs الأُخوة in b000001) → `title_variant`; author name variant with 'بن مهدي' on p.17 → `metadata_conflict` (info, additive); page count (T-031).
- Missing fields (e.g. ISBN absent) listed in `metadata.json.missing`.

## Files
- `src/ilm_engine/processors/metadata.py`
- `tests/test_metadata_conflicts.py`

## Implementation notes
- Variants are recorded, never auto-resolved.

## Acceptance criteria
- [ ] Issue `title_variant` with both forms and anchors.
- [ ] `missing` contains at least `isbn`.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_metadata_conflicts.py -q
```

## Out of scope
- Anything not listed in Scope.
