---
id: T-072
title: "Rule-based unit facts"
epic: E07
priority: P1
depends_on: [T-071, T-062]
estimate: M
owner: agent
status: todo
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
- [ ] Unit #8 facts: converted_to_islam (anchor 60–65 'أسلمت'), married (70–76), has_narration=false (78–97 'ولم يُروَ عنها شيءٌ').
- [ ] Every fact anchor satisfies text[start:end]==quote.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_unit_facts.py -q
```

## Out of scope
- LLM facts (T-094).
