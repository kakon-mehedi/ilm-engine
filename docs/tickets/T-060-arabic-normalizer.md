---
id: T-060
title: "Arabic search normalizer"
epic: E06
priority: P0
depends_on: [T-001]
estimate: S
owner: agent
status: todo
wave: 1
---

# T-060 — Arabic search normalizer

**Epic:** E06 Arabic NLP · **Priority:** P0 · **Estimate:** S · **Wave:** 1

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement D: diacritics and spelling variation. Normalized text is a DERIVED copy for matching/search only; originals are never overwritten.

## Scope
- `normalize(text, profile='search') -> str` rules: strip tashkeel/harakat + shadda + sukun + superscript alef; remove tatweel; أ/إ/آ/ٱ → ا; ى → ي; ة → ه (search profile only); normalize 'اللَّه' → 'الله'; unify honorifics '-صلى الله عليه وسلم-' / 'ﷺ' → token 'ﷺ'; collapse whitespace; Arabic-Indic digits kept (see T-061).
- `profile='match'` (milder: no ة→ه) for evidence matching.
- `normalize_with_map(text)` returning normalized string + index map back to original offsets (needed by evidence guard).

## Files
- `src/ilm_engine/nlp/normalize.py`
- `tests/test_normalize.py`

## Implementation notes
- Pure Python, no dependencies.

## Acceptance criteria
- [ ] normalize('الدَّارقطني') == normalize('الدارقطني') == normalize('الدَّارَقُطْنِيّ').
- [ ] normalize('رسول اللَّه -صلى الله عليه وسلم-') == normalize('رسول الله ﷺ').
- [ ] Index map: for every normalized char, mapped original offset points to the source char it came from (property test on b000135).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_normalize.py -q
```

## Out of scope
- Morphology (T-063).
