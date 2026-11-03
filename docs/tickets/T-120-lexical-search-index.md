---
id: T-120
title: "Normalized lexical search index"
epic: E12
priority: P1
depends_on: [T-060, T-071]
estimate: S
owner: agent
status: todo
wave: 9
---

# T-120 — Normalized lexical search index

**Epic:** E12 Search · **Priority:** P1 · **Estimate:** S · **Wave:** 9

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement D: search that tolerates diacritics and spelling variants (MVP stand-in for OpenSearch).

## Scope
- `search/lexical.py`: inverted index over normalized tokens of blocks + units + entity names; BM25 scoring; results return anchors.
- Write `search_index.json`.

## Files
- `src/ilm_engine/search/lexical.py`
- `tests/test_lexical.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Query 'الدارقطني' and 'الدَّارقطني' return identical result lists.
- [ ] Query 'هند بنت عتيق' ranks unit #8 first.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_lexical.py -q
```

## Out of scope
- Anything not listed in Scope.
