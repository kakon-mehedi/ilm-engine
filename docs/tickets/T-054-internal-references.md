---
id: T-054
title: "Internal cross-references"
epic: E05
priority: P1
depends_on: [T-070, T-053]
estimate: S
owner: agent
status: todo
wave: 8
---

# T-054 — Internal cross-references

**Epic:** E05 Annotations, citations, related works · **Priority:** P1 · **Estimate:** S · **Wave:** 8

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement E: internal references such as 'ترجمة رقم (٣٣)' (b000063, p.11) and 'كما سيأتي'.

## Scope
- Patterns: 'ترجمة رقم \((N)\)', 'رقم \((N)\)' in non-citation context, 'كما سيأتي', 'كما تقدم'.
- Resolve numbered ones to the knowledge unit of entry N → annotation `type:'internal_ref'`.
- Unresolvable → `unresolved_internal_ref`.

## Files
- `src/ilm_engine/processors/citations.py`
- `tests/test_internal_refs.py`

## Implementation notes
- Don't confuse with hadith numbers 'رقم: ١٣٨٢' inside takhrij.

## Acceptance criteria
- [ ] b000063 'ترجمة رقم (٣٣)' links to entry 33's unit.
- [ ] 'رقم: ١٣٨٢' in b000133 is NOT an internal ref.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_internal_refs.py -q
```

## Out of scope
- Anything not listed in Scope.
