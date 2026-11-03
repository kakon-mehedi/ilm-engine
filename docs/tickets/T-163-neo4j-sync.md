---
id: T-163
title: "Neo4j knowledge-graph sync"
epic: E16
priority: P2
depends_on: [T-143]
estimate: L
owner: agent
status: backlog
wave: 13
---

# T-163 — Neo4j knowledge-graph sync

**Epic:** E16 Production backlog · **Priority:** P2 · **Estimate:** L · **Wave:** 13

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Derived graph for discovery and cross-book links. Design-level ticket for the production phase (see docs/02-architecture.md and 08-roadmap.md).

## Scope
- Nodes Person/Work/Concept/Event/Unit; edges from relations + cites + work relations; only approved items; rebuild job.

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
