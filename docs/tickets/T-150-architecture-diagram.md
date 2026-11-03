---
id: T-150
title: "Deliverable 1: System architecture diagram"
epic: E15
priority: P0
depends_on: []
estimate: S
owner: agent
status: todo
wave: 0
---

# T-150 — Deliverable 1: System architecture diagram

**Epic:** E15 Assignment deliverables · **Priority:** P0 · **Estimate:** S · **Wave:** 0

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Assignment §5.1. Source: docs/02-architecture.md.

## Scope
- `deliverables/diagrams/system-architecture.mmd` (Mermaid): sources → adapter registry → canonical → immutable store; processing workers; 4 agents; LLM gateway; validation; review; stores (Postgres SoT → Qdrant/Neo4j/OpenSearch derived); serving; cross-cutting.
- Legend for colour coding (script/NLP/LLM-agent/human).

## Files
- `deliverables/diagrams/system-architecture.mmd`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Renders with mermaid-cli without errors; every component in 02-architecture.md appears.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
npx -y @mermaid-js/mermaid-cli -i deliverables/diagrams/system-architecture.mmd -o /tmp/a.svg
```

## Out of scope
- Anything not listed in Scope.
