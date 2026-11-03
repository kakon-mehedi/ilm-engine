---
id: T-131
title: "Entity evaluation (precision/recall vs gold)"
epic: E13
priority: P1
depends_on: [T-130, T-081]
estimate: S
owner: agent
status: todo
wave: 12
---

# T-131 — Entity evaluation (precision/recall vs gold)

**Epic:** E13 Evaluation · **Priority:** P1 · **Estimate:** S · **Wave:** 12

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Measure extraction quality honestly.

## Scope
- `eval/gold.py`: match gold names to extracted entities by normalized name + page; compute precision, recall, F1; list misses and false positives.

## Files
- `src/ilm_engine/eval/gold.py`
- `tests/test_eval.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] `ilm-engine eval` prints P/R/F1 and writes `eval_report.json`.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run ilm-engine eval --book pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6
```

## Out of scope
- Anything not listed in Scope.
