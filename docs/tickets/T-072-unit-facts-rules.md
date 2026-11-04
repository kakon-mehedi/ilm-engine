---
id: T-072
title: "Rule-based unit facts"
epic: E07
priority: P1
depends_on: [T-071, T-062]
estimate: M
owner: agent
status: done
wave: 9
---

# T-072 — Rule-based unit facts

**Epic:** E07 Knowledge units · **Priority:** P1 · **Estimate:** M · **Wave:** 9

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Extract explicit facts with deterministic patterns before any LLM.

## Scope
- Patterns → predicates: 'أسلم/أسلمت' → converted_to_islam=true; 'لم يُروَ عنه/عنها شيء' → has_narration=false; 'له صحبة' → is_sahabi=true; 'لا صحبة له' → is_sahabi=false; 'تزوجت/تزوج' → married=true; death years 'مات/توفي سنة …' → death_hijri.
- Each fact: `{predicate, value, assertion:'stated', origin, anchor(quote exact)}`.

## Files
- `src/ilm_engine/extractors/units.py`
- `tests/test_unit_facts.py`

## Implementation notes
- Match on normalized text via index map; anchor on original text.

## Acceptance criteria
- [x] Unit #8 facts: converted_to_islam (anchor 60–65 'أسلمت'), married (70–76), has_narration=false (78–97 'ولم يُروَ عنها شيءٌ').
- [x] Every fact anchor satisfies text[start:end]==quote.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_unit_facts.py -q
```

## Out of scope
- LLM facts (T-094).

## Follow-ups
- Rules run on the `match`-normalized copy of the unit's own spans and map back with the offset map; quotes are exact and trimmed. Predicates: `converted_to_islam`, `married`, `has_narration` (false), `is_sahabi` (true/false), `death_hijri` (digits or number words). Arabic-letter word boundaries, so "الإسلام" is not "أسلم" and "وتزوجت،" still matches.
- The death rule allows only a place ("بالطائف") or a time phrase ("في شهر …") between the verb and "سنة": b000294's "ومات أبو سفيان بن الحارث سنة عشرين" (another person) is not attributed to entry 32. On the sample: married 22, converted_to_islam 9, death_hijri 3, has_narration 1, is_sahabi 1.
- Facts: `stated`, origin of the evidence block, rule confidence 0.95.
- The `units` step now adds the LLM pass when a provider is configured (T-094 extraction + T-102 consensus, only predicates the rules did not state; model outputs kept for review items). With the null provider it records one book-level `needs_llm` issue rather than 75 per-unit issues, so the review queue is not flooded.
