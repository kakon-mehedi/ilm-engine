---
id: T-154
title: "Submission README & checklist"
epic: E15
priority: P1
depends_on: [T-153, T-143]
estimate: S
owner: agent
status: todo
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
- [ ] Fresh clone + quickstart works on a clean machine (CI-like run in tmp dir).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv sync && uv run ilm-engine run --input data
```

## Out of scope
- Anything not listed in Scope.
