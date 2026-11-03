---
id: T-083
title: "Relation kinds (full/paternal/maternal) incl. لأم ولد rule"
epic: E08
priority: P0
depends_on: [T-082]
estimate: S
owner: agent
status: todo
wave: 12
---

# T-083 — Relation kinds (full/paternal/maternal) incl. لأم ولد rule

**Epic:** E08 Entities & relationships · **Priority:** P0 · **Estimate:** S · **Wave:** 12

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Sibling relations need a kind. 'لأم ولد' (b000349) means the mother was an umm walad — it is NOT a maternal-sibling marker.

## Scope
- `sibling_of.kind`: `full` (same father & mother stated), `paternal` (same father, different/unknown mother), `maternal` ('لأمه', 'من أمهم X' with named mother, e.g. Khadija section), `unknown`.
- Rule: 'لأم ولد' → mother_status='umm_walad', kind stays paternal/unknown.
- Mother relations `mother_is` from 'وأمهم/أمه X'.

## Files
- `src/ilm_engine/extractors/relations.py`
- `tests/test_relation_kinds.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] b000349 ('ابنا العباس لأم ولد') → kind != maternal, mother_status umm_walad.
- [ ] Khadija section units (#8–#10) get maternal sibling relation to the Prophet's children (inferred, see T-084).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_relation_kinds.py -q
```

## Out of scope
- Anything not listed in Scope.
