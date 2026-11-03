---
id: T-041
title: "Metadata derived from book content"
epic: E04
priority: P1
depends_on: [T-040, T-034, T-060]
estimate: M
owner: agent
status: done
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
- [x] `author.death_hijri` = 385 with anchor in b000049 and `source: 'book_content'`.
- [x] `volume_note` = part 1 of 2 with anchors b000002 and b000591.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_metadata_content.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `content_metadata(book, record, origins, structure, config, llm_available)` returns the record with `book_content` sources (anchors) added, the findings, and issues. Findings: title (b000001), author name (line after "للحافظ", b000004), editor (line after "تحقيق", b000008), death year from the title page (b000005, digits) and from the section about the author (b000049 [24:51] "سنةٍ خمسٍ وثمانين وثلاث مئة" → 385 via `words_to_int`). The death-year search is limited to the title page and sections whose title names the author, so other people's death dates are not taken.
- Card values are never overwritten here; content evidence is appended as a second source (values that differ are T-042's conflicts).
- `BookMetadata.volume_note` (new; added to 03-data-contracts §7 and the schemas) = `{part: 1, of_at_least: 2}` with anchors b000002 «الجزء الأول» and b000591 "لم أجد الجزء الثاني".
- The `metadata` step now also needs `structure` and reads the `llm` config section. Without an LLM provider it records `needs_llm` for the `metadata_verify` pass; with a provider the pass is left for a follow-up (rules cover the sample).
