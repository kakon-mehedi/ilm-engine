---
id: T-060
title: "Arabic search normalizer"
epic: E06
priority: P0
depends_on: [T-001]
estimate: S
owner: agent
status: done
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
- [x] normalize('الدَّارقطني') == normalize('الدارقطني') == normalize('الدَّارَقُطْنِيّ').
- [x] normalize('رسول اللَّه -صلى الله عليه وسلم-') == normalize('رسول الله ﷺ').
- [x] Index map: for every normalized char, mapped original offset points to the source char it came from (property test on b000135).
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_normalize.py -q
```

## Out of scope
- Morphology (T-063).

## Follow-ups
- Implemented ADR-012 where it differs from this ticket (ADRs take precedence; 04-edge-cases EC-062, 06-ai-strategy and PRD FR-050 agree with the ADR): honorifics become the token `<SAW>` (not `ﷺ`), Arabic-Indic digits become 0–9 in the normalized copy, and ؤ → و, ئ → ي are applied. Entry detection runs on the original text, so it is unaffected.
- `normalize_with_map` returns `NormalizedText(text, starts, ends)`: each normalized character carries the original span it came from; removed marks are attached to the preceding letter, so `to_original(start, end)` returns the full original span including trailing diacritics (b000135: "ولم يرو عنها شيء" → 78–97). `index_map` is `starts`.
- Profiles: `search` (all rules) and `match` (keeps ة). Zero-width and bidi marks are also removed.
- `NORMALIZER_VERSION = "1.0.0"` is exported for the run manifest (T-141).
- On the sample, 137 honorifics are tokenized: 134 plain + 3 with diacritics (EC-062 counts only the 134 plain ones).
