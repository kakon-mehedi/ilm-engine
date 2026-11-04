---
id: T-154
title: "Submission README & checklist"
epic: E15
priority: P1
depends_on: [T-153, T-143]
estimate: S
owner: agent
status: done
wave: 15
---

# T-154 — Submission README & checklist

**Epic:** E15 Assignment deliverables · **Priority:** P1 · **Estimate:** S · **Wave:** 15

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Make it trivial for the reviewer to run and read.

## Scope
- Root `README.md` for the submission: what's inside, 3-command quickstart (`uv sync`, `ilm-engine run`, open `review.html`), where outputs are, known limitations, open questions.
- Checklist of assignment deliverables with links.

## Files
- `README.md`
- `deliverables/SUBMISSION_CHECKLIST.md`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] Fresh clone + quickstart works on a clean machine (CI-like run in tmp dir).
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv sync && uv run ilm-engine run --input data
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- Root `README.md` rewritten for the submission: results on the sample, principles, 3-command quickstart (`uv sync`, `ilm-engine run --input data`, open `review.html`), other commands, output files, architecture, layout, known limitations, open questions, documentation map.
- `deliverables/SUBMISSION_CHECKLIST.md`: every assignment deliverable (§5) and technical consideration (§6) with links and how it is verified, plus a pre-submission checklist.
- Fresh-clone check: a clean `git clone` of this branch with only the two sample files copied into `data/` → `uv sync`, `ilm-engine run --input data` (all 21 steps ran, `review.html` written) and `pytest` (671 passed, 9 skipped: the adapter golden tests skip because their confidential excerpt is git-ignored).
