---
id: T-071
title: "Knowledge unit assembly (entry + footnotes + section)"
epic: E07
priority: P0
depends_on: [T-070, T-050, T-051, T-035]
estimate: M
owner: agent
status: todo
wave: 8
---

# T-071 — Knowledge unit assembly (entry + footnotes + section)

**Epic:** E07 Knowledge units · **Priority:** P0 · **Estimate:** M · **Wave:** 8

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
A knowledge unit = the entry text (author) + its footnotes (editor) + its section context, each with origin and anchors.

## Scope
- `KnowledgeUnit{id, type:'biographical_entry', genre:'biography', subgenre:'ansab', entry_no, section_id, origin:'author_text', anchors[], annotations[] (entry footnote + inline footnotes incl. continuations), facts[], entities[], extraction{method, models, prompt_versions, confidence, review_status}}`.
- Entry footnote = ref at entry start (marker 'N -').

## Files
- `src/ilm_engine/extractors/units.py`
- `tests/test_units.py`

## Implementation notes
- IDs via `make_id('ku', pub_ref, f'entry:{n}')`.

## Acceptance criteria
- [ ] 75 units; 74 have an entry footnote; unit #32 has none → issue `entry_without_footnote`.
- [ ] Unit #8 annotations = [b000139, b000140, b000141, b000142]; section = Khadija section; anchors = b000135 [0,102].
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_units.py -q
```

## Out of scope
- Anything not listed in Scope.
