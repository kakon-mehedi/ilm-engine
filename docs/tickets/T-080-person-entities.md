---
id: T-080
title: "Person entities from units and footnotes"
epic: E08
priority: P0
depends_on: [T-072, T-062]
estimate: M
owner: agent
status: done
wave: 10
---

# T-080 — Person entities from units and footnotes

**Epic:** E08 Entities & relationships · **Priority:** P0 · **Estimate:** M · **Wave:** 10

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement G: identify entities. One entity per biographical subject + persons in nasab chains + named mothers.

## Scope
- `Entity{id, type:'person', canonical_name, name: Name, gender, aliases[], mentions[anchors], origin_of_mentions}` in `entities.json`.
- Entry subject may be elliptic ('٩ - وهند.') → inherit chain from closing phrase (T-082) or mark `needs_llm`.
- Also: author (الدارقطني), editor, Prophet (fixed authority id `ent_prophet` with aliases رسول الله, النبي, ﷺ).

## Files
- `src/ilm_engine/extractors/entities.py`
- `tests/test_entities.py`

## Implementation notes
- Entry #9 'وهند' is Hind ibn Abi Hala (male) — not Hind bint Atiq (#8).

## Acceptance criteria
- [x] ≥ 75 person entities (one per entry subject).
- [x] Entity for entry #8 has gender f, chain starting 'عتيق'.
- [x] Entity for entry #9 gender m after T-082 runs.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_entities.py -q
```

## Out of scope
- Cross-book authority linking (production).

## Follow-ups
- `build_entities(book, units, metadata, origins, config) -> Entities{entities, unit_subjects, issues}`: 75 subject entities (mention anchored at the parsed name span, e.g. #8 b000135 [4:58]), plus the Prophet (`ent_prophet`, aliases رسول الله / النبي / ﷺ, first 20 mentions in the author's text), the author (card name, `external_ids.shamela_author` from the source attributes, mention b000004) and the editor (mention b000008).
- Entity IDs: `ent` + `normalized canonical name|first anchor` (ADR-011); `ent_prophet` is a fixed authority ID as the ticket specifies.
- The step links each unit's `subject_entity_id` (linked units are passed on in the step data and used by validation and search).
- Elliptic subjects (#9 "وهند") keep gender `unknown` and no chain here; T-082 fills both from the group closure ("ابنا أبي هالة").
