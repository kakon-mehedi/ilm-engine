---
id: T-082
title: "Sibling grouping by closing phrases"
epic: E08
priority: P0
depends_on: [T-080]
estimate: M
owner: agent
status: todo
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
- [ ] Entries #9 and #10 grouped by 'ابنا أبي هالة مالك' (b000137): sibling_of(#9,#10), child_of(#9, أبو هالة مالك), child_of(#10, …).
- [ ] Entries #18–#21 'بنو عبد المطلب' (b000218) form one group.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_sibling_groups.py -q
```

## Out of scope
- Anything not listed in Scope.
