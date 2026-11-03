---
id: T-132
title: "Evaluation & run summary report"
epic: E13
priority: P1
depends_on: [T-131, T-141]
estimate: S
owner: agent
status: todo
wave: 13
---

# T-132 — Evaluation & run summary report

**Epic:** E13 Evaluation · **Priority:** P1 · **Estimate:** S · **Wave:** 13

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Numbers for the proposal: what the system found, what went to review, quality.

## Scope
- `output/<pub_ref>/SUMMARY.md` generated: counts (blocks, units, entities, relations stated/inferred, citations, issues by code, review items by reason), eval metrics, run manifest excerpt.

## Files
- `src/ilm_engine/eval/summary.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria

- [ ] Report reads `eval_report.json` (from T-131) and the run outputs; adds them to the run summary.
- [ ] SUMMARY.md lists 594 blocks, 75 units, 300 refs resolved, 16 continuations, 1 nested footnote, review counts.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run ilm-engine run --input data && test -f output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6/SUMMARY.md
```

## Out of scope
- Anything not listed in Scope.
