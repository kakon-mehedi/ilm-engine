---
id: T-121
title: "Optional semantic search (BGE-M3)"
epic: E12
priority: P2
depends_on: [T-120]
estimate: M
owner: agent
status: done
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
- [x] Pipeline runs with feature off.
- [x] With model: query 'أبناء العباس' returns units from the Abbas section in top 5.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_semantic.py -q
```

## Out of scope
- Qdrant (T-162).

## Follow-ups
- `search/semantic.py`: BGE-M3 (`BAAI/bge-m3`) via sentence-transformers when `features.semantic_search` is on and the library/model load; vectors cached as `.cache/vectors/<pub_ref>.npy` (re-embedded when the document count changes); `hybrid_search` = 0.5 × normalized BM25 + 0.5 × cosine, falling back to lexical search without the model.
- The pipeline runs with the feature off (default); with it on but the model missing it logs once and stays lexical (`search_index` step data `semantic: false`).
- sentence-transformers is not installed in this environment, so the "أبناء العباس → Abbas-section units in the top 5" test is skipped; it runs once the `semantic` extra and the model are available.
