---
id: T-041
title: "Metadata derived from book content"
epic: E04
priority: P1
depends_on: [T-040, T-034, T-060]
estimate: M
owner: agent
status: todo
wave: 6
---

# T-041 — Metadata derived from book content

**Epic:** E04 Metadata · **Priority:** P1 · **Estimate:** M · **Wave:** 6

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement A: use preface/intro/conclusion to confirm and enrich metadata.

## Scope
- Rule extractors on `editor_text`/title pages: author death sentence ('سنة خمس وثمانين وثلاث مئة' → 385) in b000049 p.9; title page b000001–b000007; manuscript title page p.17; volume statement '«الجزء الأول»' (b000002); end note 'لم أجد الجزء الثاني' (b000591).
- Each value with an anchor (quote must match exactly).
- Optional LLM pass (provider null → skipped, issue `needs_llm`).

## Files
- `src/ilm_engine/processors/metadata.py`
- `tests/test_metadata_content.py`

## Implementation notes
- Arabic number words → int helper in `nlp/arabic_digits.py`.

## Acceptance criteria
- [ ] `author.death_hijri` = 385 with anchor in b000049 and `source: 'book_content'`.
- [ ] `volume_note` = part 1 of 2 with anchors b000002 and b000591.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_metadata_content.py -q
```

## Out of scope
- Anything not listed in Scope.
