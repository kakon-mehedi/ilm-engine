---
id: T-061
title: "Arabic-Indic digits and number words"
epic: E06
priority: P0
depends_on: [T-001]
estimate: S
owner: agent
status: todo
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
- [ ] All examples above pass; 'سنةٍ خمسٍ وثمانين وثلاث مئة' (with tanween) → 385.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_arabic_digits.py -q
```

## Out of scope
- Anything not listed in Scope.
