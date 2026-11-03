---
id: T-101
title: "Rule-based validation"
epic: E10
priority: P0
depends_on: [T-100, T-071]
estimate: S
owner: agent
status: done
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
- [x] Sample run: 0 failures on anchor/hash/ID checks; report lists counts per check.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_rules.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `validation/rules.py::run_checks(book, Records)` → anchors, ids_unique, origin_present, relation_endpoints, dual_grammar, numbering, traceable; `report()` gives pass/fail, counts and failure counts per check. Anchor failures report `stale` / `orphaned` (ADR-017). Sample: 0 failures.
- The `validate` step (`validation/validate.py`) also applies sensitivity (T-104) to each unit's text and entry note — tagged units and facts whose evidence block is tagged go to `pending_review` with `sensitive_content` — and writes one `ValidationResult` per unit, fact, entity and relationship. `validation_report.json` = `{rules, results, decisions}`; validated records are passed on in the step data.
- Entities and relationships are validated once T-080–T-084 produce them (the step reads upstream results only if present); the dual-grammar check then covers the "ابنا" groups.
