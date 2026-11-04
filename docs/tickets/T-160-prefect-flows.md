---
id: T-160
title: "Prefect flows for the book pipeline"
epic: E16
priority: P2
depends_on: [T-143]
estimate: L
owner: agent
status: backlog
wave: 13
---

# T-160 — Prefect flows for the book pipeline

**Epic:** E16 Production backlog · **Priority:** P2 · **Estimate:** L · **Wave:** 13

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Production orchestration with retries, concurrency limits, per-book flow runs. Design-level ticket for the production phase (see docs/02-architecture.md and 08-roadmap.md).

## Scope
- Map each MVP step to a Prefect task; book flow; batch flow over a catalog; concurrency/rate limits per LLM provider; work pools on k8s.

## Files
- `(production repo)`

## Implementation notes
- Not part of the 1–2 day MVP.

## Acceptance criteria
- [ ] Design note written in `docs/` or implementation merged with tests, matching DECISIONS.md names.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
(defined when scheduled)
```

## Out of scope
- Anything not listed in Scope.
