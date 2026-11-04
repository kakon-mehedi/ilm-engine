---
id: T-071
title: "Knowledge unit assembly (entry + footnotes + section)"
epic: E07
priority: P0
depends_on: [T-070, T-050, T-051, T-035]
estimate: M
owner: agent
status: done
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
- [x] 75 units; 74 have an entry footnote; unit #32 has none → issue `entry_without_footnote`.
- [x] Unit #8 annotations = [b000139, b000140, b000141, b000142]; section = Khadija section; anchors = b000135 [0,102].
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_units.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- Contract `KnowledgeUnit` fields (genre/sub_type/unit_type, `note_annotation_ids`, `payload`, `facts`, `confidence`, `review_status`, `provenance`) replace the ticket's `extraction{…}` envelope; the payload is the biography plugin schema (`person{surface, span, ism, kunya, laqab, nisba, gender}`, `nasab`, `section_heading_block`, `tarjama_annotation`).
- **Unit IDs follow ADR-011** (`ku` + `entry_no|block_id|start`, `extractors.units.unit_id`) rather than this ticket's `entry:{n}`; ADRs take precedence, and internal references (T-054) already resolve to these IDs.
- A unit's annotations are those whose marker lies inside the unit's own spans (entries sharing a block keep their own notes); the entry note (marker "N -" at the entry start) comes first. 74 units have one; #32 raises `entry_without_footnote` (info).
- `subject_entity_id` and `facts` are filled by T-080 and T-072. The step writes `knowledge_units.json` (list of units).
