---
id: T-112
title: "Consolidated enrichment.json"
epic: E11
priority: P0
depends_on: [T-110, T-105]
estimate: S
owner: agent
status: todo
wave: 11
---

# T-112 — Consolidated enrichment.json

**Epic:** E11 Enrichment storage & export · **Priority:** P0 · **Estimate:** S · **Wave:** 11

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
One file a reviewer can open to see everything, linked to the original.

## Scope
- `enrichment.json` = {book_ref, source, integrity{canonical_content_hash, source_declared_hash, verified}, metadata, structure, origin_summary, annotations, citations, related_works, knowledge_units, entities, relationships, issues, review_summary, run_manifest_ref}.
- JSON Schema file `docs/enrichment.schema.json` generated from Pydantic.

## Files
- `src/ilm_engine/storage/json_store.py`
- `docs/enrichment.schema.json`
- `tests/test_enrichment_json.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] enrichment.json validates against the schema.
- [ ] Every fact/unit has ≥1 anchor and an origin.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_enrichment_json.py -q
```

## Out of scope
- Anything not listed in Scope.
