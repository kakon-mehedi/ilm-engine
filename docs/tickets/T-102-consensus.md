---
id: T-102
title: "Multi-model consensus & discrepancy detection"
epic: E10
priority: P1
depends_on: [T-094]
estimate: M
owner: agent
status: todo
wave: 5
---

# T-102 — Multi-model consensus & discrepancy detection

**Epic:** E10 Validation & human review · **Priority:** P1 · **Estimate:** M · **Wave:** 5

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Section 3.7: model comparison, independent validation, consensus, discrepancy detection.

## Scope
- Compare extractor vs verifier field-by-field (normalized values, same anchor overlap).
- Agree → agreement ×1.2; disagree → issue `model_disagreement`, optional judge (`judge.v1`, different model) → 0.9; never auto-pick a value on disagreement without judge.
- Store both outputs for the reviewer.

## Files
- `src/ilm_engine/validation/consensus.py`
- `tests/test_consensus.py`

## Implementation notes
- Example: born 1200 vs 1205 AH → disagreement → review.

## Acceptance criteria
- [ ] Fake providers agreeing → factor 1.2; disagreeing (1200 vs 1205) → `model_disagreement` and `pending_review`.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_consensus.py -q
```

## Out of scope
- Anything not listed in Scope.
