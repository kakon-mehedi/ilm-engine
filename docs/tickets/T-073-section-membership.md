---
id: T-073
title: "Section membership and group headings"
epic: E07
priority: P1
depends_on: [T-071]
estimate: S
owner: agent
status: todo
wave: 9
---

# T-073 — Section membership and group headings

**Epic:** E07 Knowledge units · **Priority:** P1 · **Estimate:** S · **Wave:** 9

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Section headings carry meaning ('* الأُخوة من ولد العباس بن عبد المطلب:') used for inferred relations.

## Scope
- Attach `section_id` and parsed `section_subject` (person after 'ولد'/'ذرية', e.g. 'العباس بن عبد المطلب') to each unit.
- Store heading anchor as evidence for inferred relations (T-084).

## Files
- `src/ilm_engine/extractors/units.py`
- `tests/test_section_membership.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Units under '* الأُخوة من ولد العباس بن عبد المطلب:' (b000339) get section_subject 'العباس بن عبد المطلب'.
- [ ] Units under 'أولاد رسول الله' (b000104) get subject 'رسول الله ﷺ'.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_section_membership.py -q
```

## Out of scope
- Anything not listed in Scope.
