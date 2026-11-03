---
id: T-080
title: "Person entities from units and footnotes"
epic: E08
priority: P0
depends_on: [T-072, T-062]
estimate: M
owner: agent
status: todo
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
- [ ] ≥ 75 person entities (one per entry subject).
- [ ] Entity for entry #8 has gender f, chain starting 'عتيق'.
- [ ] Entity for entry #9 gender m after T-082 runs.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_entities.py -q
```

## Out of scope
- Cross-book authority linking (production).
