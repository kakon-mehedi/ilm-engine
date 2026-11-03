---
id: T-101
title: "Rule-based validation"
epic: E10
priority: P0
depends_on: [T-100, T-071]
estimate: S
owner: agent
status: todo
wave: 9
---

# T-101 — Rule-based validation

**Epic:** E10 Validation & human review · **Priority:** P0 · **Estimate:** S · **Wave:** 9

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Cheap deterministic checks before/after any AI step.

## Scope
- Checks: schema valid; anchors exist and `block_hash` matches; origin present; IDs unique; relation endpoints exist; dual-grammar check; numbering continuity; every unit traceable (≥1 anchor).
- Write `validation_report.json` with pass/fail per check and counts.

## Files
- `src/ilm_engine/validation/rules.py`
- `tests/test_rules.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Sample run: 0 failures on anchor/hash/ID checks; report lists counts per check.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_rules.py -q
```

## Out of scope
- Anything not listed in Scope.
