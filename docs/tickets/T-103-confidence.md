---
id: T-103
title: "Confidence scoring"
epic: E10
priority: P0
depends_on: [T-100]
estimate: S
owner: agent
status: done
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
- [x] rule fact exact evidence valid schema → 0.95.
- [x] llm fact, 2 models agree, exact evidence → min(1, 0.75×1.2)=0.90.
- [x] llm single model → 0.75 (< 0.80 → review).
- [x] ambiguous entity penalty applied ×0.8.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_confidence.py -q
```

## Out of scope
- Calibration (production, needs reviewed data).

## Follow-ups
- `score(config, base, evidence, schema, agreement, penalties) -> Confidence{score, factors, disagreement}`; `factors` is the contract's `ConfidenceFactors`. Scores are rounded to 4 decimals (0.75 × 1.2 = 0.9 exactly).
- `agreement="disagree"` keeps the single-model factor and sets `disagreement=True`; the caller raises `model_disagreement` and the item goes to review (DECISIONS §8).
- New config key `confidence.penalties.ambiguous_quote: 0.9` for ADR-007's "several occurrences, no hint" penalty (the evidence guard's `ambiguity_penalty`).
- `threshold_for(config, category)` and `decide(config, confidence, category, sensitive)` apply `review.threshold.*`; sensitive items are never auto-approved.
