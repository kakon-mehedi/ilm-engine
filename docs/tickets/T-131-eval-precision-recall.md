---
id: T-131
title: "Entity evaluation (precision/recall vs gold)"
epic: E13
priority: P1
depends_on: [T-130, T-081]
estimate: S
owner: agent
status: done
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
- [x] `ilm-engine eval` prints P/R/F1 and writes `eval_report.json`.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run ilm-engine eval --book pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- The gold sample has entry numbers rather than pages (T-130), so matching is by entry number → unit → subject entity, then name: ism (or kunya) after normalization, ignoring the ﷺ honorific and spaces in joined compounds ("عبدالله" / "عبد الله"). Precision = correct subjects / extracted subjects, recall = matched / gold rows; misses and false positives are listed.
- `chain_agreement` also checks the first ancestor where both give one; the index may name the father by kunya ("بن أبي هالة") where the lineage has the ism ("مالك"), which counts as agreement.
- `ilm-engine eval [--book] [--out] [--gold]` prints the metrics and writes `eval_report.json`. Sample: P = R = F1 = 1.0 (75/75), chain agreement 41/41.
