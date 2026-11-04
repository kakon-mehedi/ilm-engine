---
id: T-083
title: "Relation kinds (full/paternal/maternal) incl. لأم ولد rule"
epic: E08
priority: P0
depends_on: [T-082]
estimate: S
owner: agent
status: done
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
- [x] b000349 ('ابنا العباس لأم ولد') → kind != maternal, mother_status umm_walad.
- [x] Khadija section units (#8–#10) get maternal sibling relation to the Prophet's children (inferred, see T-084).
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_relation_kinds.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- Mother statements on the normalized entry text: "أمه/أمها X" → that entry; "أمهما X" → the dual group it closes or the last two entries; "أمهم X" → the group it closes, else every entry since the previous closure or mother statement in the section (#39 "أمهم أم الفضل لبابة …" covers #33–#39). Each gives `mother_is` (stated, evidence from the pronoun to the end of the name) to a mother entity; "أمها أم ولد يقال لها: فكيهة" (#72) → `mother_status: umm_walad` with the named mother.
- Kinds on sibling relations: closure with "لأم ولد" / "لأمهات أولاد" → `paternal` + `mother_status: umm_walad` (never maternal, DECISIONS §11; b000349 #40–#41); same father and the same stated mother → `full` (#62–#63, #64–#65); same father otherwise → `paternal`. "وأخته لأمه:" (#71 → #72) adds a stated sibling relation, `full` when both share the father (here both "بن/بنت عمر"), else `maternal`.
- The Khadija-section maternal relation of #8–#10 to the Prophet's children is inferred from the heading and created in T-084.
- `nlp.nasab`: names no longer start at a leading footnote marker (kunya after "(٢)" is recognized) and `display_name()` removes inline markers from canonical names (e.g. "هند بنت عتيق بن عابد بن عبد الله …").
