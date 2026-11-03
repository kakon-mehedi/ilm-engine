---
id: T-062
title: "Nasab (lineage chain) parser"
epic: E06
priority: P0
depends_on: [T-060]
estimate: M
owner: agent
status: todo
wave: 2
---

# T-062 — Nasab (lineage chain) parser

**Epic:** E06 Arabic NLP · **Priority:** P0 · **Estimate:** M · **Wave:** 2

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Biographical names are chains: ism + 'بن/ابن/بنت' + father + … plus kunya/laqab/nisba.

## Scope
- `parse_name(text) -> Name{ism, gender, kunya, laqab, nisba, chain: list[str], raw, span}`.
- Gender: 'بنت' or feminine ism list → f; 'ابنا/بنو' handled in relations (T-082), not here.
- Stop chain at footnote markers '(١)' (skip them), punctuation '؛', '،', or verbs ('أسلمت').
- Kunya prefixes أبو/أبي/أبا/أم; nisba = trailing word starting with 'ال' ending in 'ي' (e.g. الدارقطني).

## Files
- `src/ilm_engine/nlp/nasab.py`
- `tests/test_nasab.py`

## Implementation notes
- 'ابن' inside chain (e.g. 'عبد الله ابن قرط') is treated as 'بن'.

## Acceptance criteria
- [ ] 'هند بنت عتيق بن عابد (١) بن عبد اللَّه بن عمر بن مخزوم' → ism 'هند', gender f, chain ['عتيق','عابد','عبد الله','عمر','مخزوم'].
- [ ] 'أبو الحسن علي بن عمر بن أحمد الدارقطني' → kunya 'أبو الحسن', ism 'علي', chain ['عمر','أحمد'], nisba 'الدارقطني'.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_nasab.py -q
```

## Out of scope
- Anything not listed in Scope.
