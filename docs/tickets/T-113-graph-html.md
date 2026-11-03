---
id: T-113
title: "Knowledge graph export (graph.html)"
epic: E11
priority: P2
depends_on: [T-112]
estimate: S
owner: agent
status: todo
wave: 12
---

# T-113 — Knowledge graph export (graph.html)

**Epic:** E11 Enrichment storage & export · **Priority:** P2 · **Estimate:** S · **Wave:** 12

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Visual demo of requirement G (entities and relationships, citation graph).

## Scope
- Self-contained HTML (vis-network from cdnjs, pinned version) with nodes persons/works and edges relations/cites; colour by assertion (stated vs inferred).
- Also export `graph.cypher` (Neo4j import statements) to show the production path.

## Files
- `src/ilm_engine/storage/graph_export.py`
- `tests/test_graph_export.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] graph.html opens offline-capable except CDN script; node count = entities + works.
- [ ] graph.cypher contains MERGE statements for all entities.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_graph_export.py -q
```

## Out of scope
- Anything not listed in Scope.
