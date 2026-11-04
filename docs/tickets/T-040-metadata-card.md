---
id: T-040
title: "Bibliographic metadata from source card"
epic: E04
priority: P0
depends_on: [T-012]
estimate: S
owner: agent
status: done
wave: 4
---

# T-040 — Bibliographic metadata from source card

**Epic:** E04 Metadata · **Priority:** P0 · **Estimate:** S · **Wave:** 4

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement A: title, author, editor, publisher, edition, year.

## Scope
- Parse `metadata.source_attributes` + `card[]` + `editions[]` into `metadata.json` fields; every field = `{value, source: 'existing_metadata', anchor|null, confidence}`.
- Parse Arabic-Indic numerals in edition ('الأولى، ١٤١٣ هـ - ١٩٩٣ م') → hijri 1413, gregorian 1993.

## Files
- `src/ilm_engine/processors/metadata.py`
- `tests/test_metadata_card.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] title 'الإخوة والأخوات'; author name 'أبو الحسن علي بن عمر بن أحمد الدارقطني', death hijri 385; editor 'باسم فيصل أحمد الجوابرة'; publisher 'دار الراية للنشر والتوزيع، الرياض - السعودية'; edition 1; year_hijri 1413; year_gregorian 1993; category 'الأنساب'; declared pages 72.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_metadata_card.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- Field shape follows the contract (`MetadataField{value, normalized, sources[], assertion, origin, confidence, conflicts, review_status}`) instead of the ticket's `{value, source, anchor, confidence}`. Card values: `sources = [{kind: existing_metadata, path: <json path>}]`, `stated`, origin `editor_text` (the card describes the edition), confidence = rule base 0.95 → auto-approved.
- Edition: the raw card string is the value; `normalized = {number: 1, year_hijri: 1413, year_gregorian: 1993, declared_pages: 72}` (ordinal words + Arabic-Indic years parsed).
- `language` is detected from the script of the book's text (`ar`), `volumes` from the canonical pages.
- `genre_primary` is a placeholder until the genre step (T-095); missing card values become `missing_fields`.
