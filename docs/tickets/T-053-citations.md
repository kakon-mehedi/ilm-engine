---
id: T-053
title: "Citations + related works (book family) extraction"
epic: E05
priority: P0
depends_on: [T-050, T-060]
estimate: M
owner: agent
status: done
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
- [x] Counts by raw title include الإصابة 144, أسد الغابة 67, السير 59, الطبقات الكبرى 45, الاستيعاب 31, التهذيب 32.
- [x] Citation '"الطبقات الكبرى" (٨/ ١٩)' from b000109 has volume 8, page 19 and an exact anchor.
- [x] related_works.json contains the 2 same_topic_as works from b000018 with exact anchors and origin `editor_text`.
- [x] Synthetic 'شرح صحيح البخاري' → candidate `sharh_of` 'صحيح البخاري'.
- [x] Every cited work in citations.json appears as a `cites` edge from this book.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_citations.py -q
uv run pytest tests/test_related_works.py -q
```

## Out of scope
- Resolving to external catalog IDs (production).

## Follow-ups
- **Data differs from the ticket (reported, not changed):** the footnotes quote "الإصابة" **145** times, not 144 (also in DECISIONS §7); every one of the 145 is a real citation (checked by listing them; many have no locator, e.g. `قال الحافظ في "الإصابة": …`). أسد الغابة 67, السير 59, الطبقات الكبرى 45, الاستيعاب 31, التهذيب 32 match. DECISIONS §7 should read 145.
- Citations use the contract's `Citation` (`title_raw`, `title_normalized`, `locators[]` with volume/page/number/page_label, `anchor` on the title, `author_hint`, `resolution`). Locators may chain: `"الكبير" (٣/ ١٦٦) (رقم: ٣٢٥٨)`.
- `config/works_aliases.yaml`: canonical works + aliases, `ambiguous` short titles (التهذيب, الكبير → unresolved + `ambiguous_entity` with candidates), `not_works` (الأصل, EC-052), `this_book` (self-citations of "الأخوة" resolve to this book). Unknown titles become `stub` works with resolution `unresolved`.
- Work IDs are library-wide (`make_id("wrk", "library", normalized title)`) so a work has one ID across books.
- `related_works.json` = `{works, work_relations}`: `cites` from this book to every cited work (count aggregated, first 5 anchors as evidence), 2 `same_topic_as` from b000018 (151–182, 216–250, editor_text, stated), 2 `tahqiq_of` from the editor's combined edition "الرّواة من الأُخوة والأخوات" (362–389); title patterns give inferred `sharh_of`/`hashiyah_of`/`mukhtasar_of`/`translation_of` candidates for review (none in the sample; tested synthetically).
- Internal references (`ترجمة رقم (n)`, `سيأتي`) are T-054.
