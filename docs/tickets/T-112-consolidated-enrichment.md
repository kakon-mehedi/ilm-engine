---
id: T-112
title: "Consolidated enrichment.json"
epic: E11
priority: P0
depends_on: [T-110, T-105]
estimate: S
owner: agent
status: done
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
- [x] enrichment.json validates against the schema.
- [x] Every fact/unit has ≥1 anchor and an origin.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_enrichment_json.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `enrichment.json` is the contract's `Enrichment` (03-data-contracts §18) rather than this ticket's key list: `source` holds the integrity fields (canonical content hash, declared hash, verified), `metadata` carries the genre fields from the genre step, `origin_map` the origin spans, `review_queue_ids` the review summary, `run_id` the manifest reference, and `stats` the counts. Lists are sorted by ID; issues are de-duplicated.
- Built by `storage.json_store.consolidate` in the `store` step from the validated records; review decisions already applied (non-pending queue items) set the targets' `review_status`. The same step rebuilds `enrichment.db` from the run (T-111's criteria hold on the sample: block 594, knowledge_unit 75, annotation 313 = 301 footnote links + 12 internal references). `export` writes `enrichment.json`.
- `pipeline.manifest.run_id(ctx)` is shared by the manifest and the export, so both carry the same deterministic run ID.
- `docs/enrichment.schema.json` is generated from the model; the test fails if it is out of date.
- The full pipeline now runs on the sample in ~4 s; only `integrity_verify` (T-022) is still a placeholder.
