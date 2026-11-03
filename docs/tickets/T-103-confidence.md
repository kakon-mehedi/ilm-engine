---
id: T-103
title: "Confidence scoring"
epic: E10
priority: P0
depends_on: [T-100]
estimate: S
owner: agent
status: todo
wave: 3
---

# T-103 — Confidence scoring

**Epic:** E10 Validation & human review · **Priority:** P0 · **Estimate:** S · **Wave:** 3

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Confidence comes from external, checkable signals — not the model's self-reported score.

## Scope
- Implement DECISIONS §8 formula exactly; factors from config.
- Return score + breakdown dict (stored on each item).

## Files
- `src/ilm_engine/validation/confidence.py`
- `tests/test_confidence.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] rule fact exact evidence valid schema → 0.95.
- [ ] llm fact, 2 models agree, exact evidence → min(1, 0.75×1.2)=0.90.
- [ ] llm single model → 0.75 (< 0.80 → review).
- [ ] ambiguous entity penalty applied ×0.8.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_confidence.py -q
```

## Out of scope
- Calibration (production, needs reviewed data).
