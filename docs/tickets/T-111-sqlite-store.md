---
id: T-111
title: "SQLite enrichment database"
epic: E11
priority: P1
depends_on: [T-110]
estimate: M
owner: agent
status: todo
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
- [ ] `enrichment.db` row counts: source_blocks 594, knowledge_units 75, annotations ≥ 301.
- [ ] Loading twice does not duplicate rows.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_sqlite_store.py -q
```

## Out of scope
- Anything not listed in Scope.
