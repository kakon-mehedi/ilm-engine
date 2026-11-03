---
id: T-111
title: "SQLite enrichment database"
epic: E11
priority: P1
depends_on: [T-110]
estimate: M
owner: agent
status: done
wave: 3
---

# T-111 — SQLite enrichment database

**Epic:** E11 Enrichment storage & export · **Priority:** P1 · **Estimate:** M · **Wave:** 3

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Relational shape that mirrors the production PostgreSQL schema (books, source_blocks, sections, knowledge_units, source_links, entities, relations, annotations, citations, issues, reviews, runs).

## Scope
- `storage/sqlite_store.py` with DDL in `storage/schema.sql` (same tables/columns as T-161 Postgres design).
- `source_blocks` stores block_id, page, block_hash, origin — NOT a modifiable copy of text (text is read from the original store).
- Load from JSON outputs; idempotent upsert by ID.

## Files
- `src/ilm_engine/storage/sqlite_store.py`
- `src/ilm_engine/storage/schema.sql`
- `tests/test_sqlite_store.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] `enrichment.db` row counts: source_blocks 594, knowledge_units 75, annotations ≥ 301.
- [x] Loading twice does not duplicate rows.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_sqlite_store.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- Table names follow the authoritative DDL in 03-data-contracts §19 (`block`, `knowledge_unit`, `annotation`, …), not this ticket's `source_blocks` / `knowledge_units` / `annotations`; `storage/schema.sql` is that DDL with `IF NOT EXISTS`.
- `SqliteStore(path).load(enrichment, book=None, origins=None, manifest=None)` takes the §18 consolidated shape (models or JSON) plus the canonical book, so the `store` step loads from step results; every record is upserted by ID (anchors and facts are replaced per owner), so loading twice gives identical rows. Internal references are stored in `annotation` with `type = 'internal_ref'`; review items come from an optional `review_items` list.
- The sample-run counts (knowledge units 75, annotations ≥ 301) are checked end to end in T-143, once units and annotations exist; this ticket's tests use the real 594 sample blocks and synthetic records.
