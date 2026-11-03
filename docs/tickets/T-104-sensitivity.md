---
id: T-104
title: "Sensitivity rules (always human review)"
epic: E10
priority: P0
depends_on: [T-095]
estimate: S
owner: agent
status: todo
wave: 6
---

# T-104 — Sensitivity rules (always human review)

**Epic:** E10 Validation & human review · **Priority:** P0 · **Estimate:** S · **Wave:** 6

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Religiously sensitive outputs always go to a human, whatever their confidence.

## Scope
- `validation/sensitivity.py` tags items with categories: `prophetic_attribution` (c1 spans / quoted Prophetic speech, 'قال رسول الله'), `hadith_grading` (صحيح/حسن/ضعيف/موضوع near إسناد), `fiqh_ruling`, `aqeedah_proposition`, `narrator_disambiguation`.
- Tagged → issue `sensitive_content` + status `pending_review`.

## Files
- `src/ilm_engine/validation/sensitivity.py`
- `tests/test_sensitivity.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] b000228 grading 'وإسناده ضعيف' → hadith_grading → pending_review even with confidence 0.95.
- [ ] The 8 c1 spans produce prophetic_attribution tags.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_sensitivity.py -q
```

## Out of scope
- Anything not listed in Scope.
