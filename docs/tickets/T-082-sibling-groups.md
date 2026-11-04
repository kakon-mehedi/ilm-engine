---
id: T-082
title: "Sibling grouping by closing phrases"
epic: E08
priority: P0
depends_on: [T-080]
estimate: M
owner: agent
status: done
wave: 11
---

# T-082 — Sibling grouping by closing phrases

**Epic:** E08 Entities & relationships · **Priority:** P0 · **Estimate:** M · **Wave:** 11

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Consecutive entries are closed by a group phrase: 'ابنا أبي هالة' (dual), 'بنو عبد المطلب' (plural), 'وأختهم:'. That phrase defines who are siblings and who the father is.

## Scope
- Detect closing phrases (ابنا / ابنتا / بنو / بنات / إخوة …) in entry text; the group = entries since previous closing phrase within the same section.
- Grammar check: dual ابنا → exactly 2 entries else penalty ×0.7 + review.
- Create `sibling_of` for all pairs and `child_of` to the named father; ambiguous group bounds → `needs_llm`.

## Files
- `src/ilm_engine/extractors/relations.py`
- `tests/test_sibling_groups.py`

## Implementation notes
- Sample: 7 author blocks contain 'ابنا', 6 contain 'بنو '.

## Acceptance criteria
- [x] Entries #9 and #10 grouped by 'ابنا أبي هالة مالك' (b000137): sibling_of(#9,#10), child_of(#9, أبو هالة مالك), child_of(#10, …).
- [x] Entries #18–#21 'بنو عبد المطلب' (b000218) form one group.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_sibling_groups.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- A closing phrase (ابنا / ابنتا / بنو / بنات + parent) counts only inside an entry's first span, ≤ 80 characters after the parsed name; narrative uses (b000147 "روى عنه ابنا أخته", b000414 "… ابنا عبد الله") and tribal "بني" are not closures.
- **Group bounds:** a dual closes the last two entries of the section (#9–#10, #40–#41, #46–#47, #62–#63, #64–#65); a plural closes every entry since the previous closure in the section (#18–#21, #22–#26, #27–#32, #54–#57). "بنات" drops members known to be male (#42 الحارث بن العباس from "بنات العباس"). With the plural "previous closure" rule alone, #8 Hind bint Atiq would wrongly join #9–#10, hence the dual rule. Fewer than 2 members → `grammar_mismatch` penalty (×0.7) → review.
- Relations: `sibling_of` per pair (kind `unknown` until T-083) and `child_of` to the parent, all with the closure phrase as evidence and `group_id` / `via_parent_entity_id`. Parent entities are new records from the parsed closure ("أبي هالة مالك بن النباش بن زرارة"); linking them to existing entries with the same name (e.g. "عمر" ↔ entry #54) is not attempted (left for review / T-081-style merging later).
- Elliptic subjects inherit the parent's lineage (#9 → "هند بن أبي هالة", nasab [مالك, النباش, زرارة], disambiguation `resolved`) and an unknown gender becomes m from a masculine closure; known genders are kept (#63 رقية stays f).
- The relations step outputs the updated entities; validation and search use them. `search_index` now also depends on `relations`.
