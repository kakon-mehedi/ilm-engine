---
id: T-151
title: "Deliverable 2: Automation & data-flow diagram"
epic: E15
priority: P0
depends_on: []
estimate: S
owner: agent
status: todo
wave: 0
---

# T-151 — Deliverable 2: Automation & data-flow diagram

**Epic:** E15 Assignment deliverables · **Priority:** P0 · **Estimate:** S · **Wave:** 0

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Assignment §5.2 + §4 (12 steps) incl. agents, scripts, databases, human review.

## Scope
- `deliverables/diagrams/data-flow.mmd`: all 12 steps numbered as in the assignment, each node coloured by method; databases as cylinders; human review loop; sensitive path.
- `deliverables/diagrams/adapter-flow.mmd`: JSON variants → adapters → canonical.
- `deliverables/diagrams/agent-workflow.mmd`: 4 agents + tools.

## Files
- `deliverables/diagrams/data-flow.mmd`
- `deliverables/diagrams/adapter-flow.mmd`
- `deliverables/diagrams/agent-workflow.mmd`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] All 12 assignment steps present verbatim-numbered; renders without errors.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
npx -y @mermaid-js/mermaid-cli -i deliverables/diagrams/data-flow.mmd -o /tmp/d.svg
```

## Out of scope
- Anything not listed in Scope.
