---
id: T-053
title: "Citations + related works (book family) extraction"
epic: E05
priority: P0
depends_on: [T-050, T-060]
estimate: M
owner: agent
status: todo
wave: 7
---

# T-053 — Citations + related works (book family) extraction

**Epic:** E05 Annotations, citations, related works · **Priority:** P0 · **Estimate:** M · **Wave:** 7

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirements B/G: footnotes cite other works — this builds the related-works/citation graph.

## Scope
- Extract quoted titles in footnotes ("…" / «…») with optional locator '(٨/ ١٥٧)' → `Citation{id, work_title_raw, work_title_norm, work_id, volume, page, number, anchor}` in `citations.json`.
- Work dictionary in config (aliases: 'الطبقات' → 'الطبقات الكبرى'?, 'التهذيب' variants) — ambiguous alias → `ambiguous_entity`.
- Aggregate counts per work.
- `extractors/related_works.py` (pipeline step `related_works`) → `related_works.json`: `Work{id, title_raw, title_norm, author_raw, relation, evidence_anchor, origin}` with work relations from DECISIONS §11 (`cites`, `same_topic_as`, `sharh_of`, `hashiyah_of`, `mukhtasar_of`, `translation_of`, `edition_of`, `tahqiq_of`).
- Related works from the editor's preface b000018: 'الأُخوة الذين رُويَ عنهم الحديث' (أبو داود السجستاني) and 'تسمية من رُويَ عنه من أولاد العشرة' (علي بن المديني) → `same_topic_as`; the editor's combined edition 'الرّواة من الأُخوة والأخوات' → `edition_of`/`tahqiq_of` (by the same muhaqqiq).
- Title patterns for Sharh/Hashiyah/Mukhtasar ('شرح', 'حاشية', 'مختصر', 'ترجمة') produce candidate work relations (none expected in this book; tested with synthetic strings).

## Files
- `src/ilm_engine/processors/citations.py`
- `config/works_aliases.yaml`
- `tests/test_citations.py`
- `src/ilm_engine/extractors/related_works.py`
- `tests/test_related_works.py`

## Implementation notes
- Quotes may be plain " in this source.

## Acceptance criteria
- [ ] Counts by raw title include الإصابة 144, أسد الغابة 67, السير 59, الطبقات الكبرى 45, الاستيعاب 31, التهذيب 32.
- [ ] Citation '"الطبقات الكبرى" (٨/ ١٩)' from b000109 has volume 8, page 19 and an exact anchor.
- [ ] related_works.json contains the 2 same_topic_as works from b000018 with exact anchors and origin `editor_text`.
- [ ] Synthetic 'شرح صحيح البخاري' → candidate `sharh_of` 'صحيح البخاري'.
- [ ] Every cited work in citations.json appears as a `cites` edge from this book.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_citations.py -q
uv run pytest tests/test_related_works.py -q
```

## Out of scope
- Resolving to external catalog IDs (production).
