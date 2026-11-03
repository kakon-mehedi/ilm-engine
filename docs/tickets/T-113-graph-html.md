---
id: T-113
title: "Knowledge graph export (graph.html)"
epic: E11
priority: P2
depends_on: [T-112]
estimate: S
owner: agent
status: done
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
- [x] graph.html opens offline-capable except CDN script; node count = entities + works.
- [x] graph.cypher contains MERGE statements for all entities.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_graph_export.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `storage/graph_export.py`: nodes = entities + works, edges = person relationships + work relations (label = type and sibling kind, colour/dashes by assertion). `graph.html` embeds the data and loads vis-network 9.1.9 from cdnjs (pinned; URL checked); without the CDN it shows a node/edge count instead of failing. `graph.cypher` has `MERGE` statements for every node and edge. Both are written by the `export` step.
- `ilm-engine rebuild-derived <out_dir> [--store]` (`storage/derived.py`) rebuilds `search_index.json`, `graph.html` and `graph.cypher` from `enrichment.db` plus the block text in the read-only original store; the test deletes all three and checks the rebuilt files are byte-identical (closes T-142's deferred `rebuild-derived` criterion). To make that hold, the search index and graph builders sort their inputs by ID.
