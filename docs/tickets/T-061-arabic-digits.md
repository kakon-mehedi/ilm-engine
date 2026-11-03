---
id: T-061
title: "Arabic-Indic digits and number words"
epic: E06
priority: P0
depends_on: [T-001]
estimate: S
owner: agent
status: done
wave: 1
---

# T-061 — Arabic-Indic digits and number words

**Epic:** E06 Arabic NLP · **Priority:** P0 · **Estimate:** S · **Wave:** 1

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Entries, locators and dates use Arabic-Indic digits; dates also appear as words.

## Scope
- `to_int('٧٥') == 75`, `to_arabic_digits(32) == '٣٢'`.
- `words_to_int('خمس وثمانين وثلاث مئة') == 385` (units, tens, hundreds incl. 'مئة/مائة', with/without tashkeel).
- Locator parser `'(٨/ ١٥٧)' -> (8, 157)`.

## Files
- `src/ilm_engine/nlp/arabic_digits.py`
- `tests/test_arabic_digits.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] All examples above pass; 'سنةٍ خمسٍ وثمانين وثلاث مئة' (with tanween) → 385.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_arabic_digits.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `words_to_int` follows Arabic word order (units, then tens, then hundreds) and applies a multiplier only to the unit just before it, so "خمس وثمانين وثلاث مئة" = 5 + 80 + 300. It also handles teens (ثلاثة عشر), joined hundreds (أربعمائة), duals (مائتين, ألفين) and thousands (ألف وأربعمائة وثلاثة عشر = 1413). Words before/after the phrase (e.g. "سنة") are skipped; an unknown word inside it raises. Verified on the real b000049 [24:51] → 385.
- `parse_locator` covers `(vol/ page)` and `(page)`; the other locator forms `(ص: n)` and `(رقم: n)` belong to the citation parser (T-053).
- Self-contained (strips diacritics itself) because this ticket depends only on T-001, not on the normalizer.
