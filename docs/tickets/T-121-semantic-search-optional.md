---
id: T-121
title: "Optional semantic search (BGE-M3)"
epic: E12
priority: P2
depends_on: [T-120]
estimate: M
owner: agent
status: todo
wave: 10
---

# T-121 — Optional semantic search (BGE-M3)

**Epic:** E12 Search · **Priority:** P2 · **Estimate:** M · **Wave:** 10

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement D: semantic/contextual retrieval. Optional; skipped cleanly when the model is not installed.

## Scope
- `search/semantic.py`: embed units and blocks with BGE-M3 via sentence-transformers if `features.semantic_search`; store vectors in `.cache/vectors.npy`; hybrid score = 0.5 BM25 + 0.5 cosine.
- Without the model: log once, feature off.

## Files
- `src/ilm_engine/search/semantic.py`
- `tests/test_semantic.py`

## Implementation notes
- Tests skipped if sentence-transformers missing.

## Acceptance criteria
- [ ] Pipeline runs with feature off.
- [ ] With model: query 'أبناء العباس' returns units from the Abbas section in top 5.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_semantic.py -q
```

## Out of scope
- Qdrant (T-162).
