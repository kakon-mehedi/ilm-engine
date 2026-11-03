---
id: T-054
title: "Internal cross-references"
epic: E05
priority: P1
depends_on: [T-070, T-053]
estimate: S
owner: agent
status: done
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
- [x] b000063 'ترجمة رقم (٣٣)' links to entry 33's unit.
- [x] 'رقم: ١٣٨٢' in b000133 is NOT an internal ref.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_internal_refs.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `internal_refs(book, unit_ids_by_entry)` returns the contract's `InternalRef` records (prefix `ann`) plus `unresolved_internal_ref` (info) issues; written as `internal_refs` in `citations.json`. The citations step runs entry detection to know the units; `extractors/units.py::unit_id` is the unit ID T-071 assigns (`entry_no|block_id|start`).
- Forms found in the sample: `ترجمة رقم (٣٣)` (b000063 → entry 33), `تقدمت برقم (٧٤)` / `تقدمت ترجمتها، برقم (١٤)` (backward by number → resolved), `تقدمت ترجمته (ص: ٢٨)` (backward by printed page → unresolved, page kept), `كما سيأتي` / `سيأتي تخريجه` (forward → unresolved), `وتقدم … في ترجمة أخيه` (backward by name → unresolved).
- Not internal references: hadith numbers `(رقم: ١٣٨٢)` and a bare `رقم (n)` right after a citation locator (b000214 `"الكبير" (١/ ٣٢) رقم (٩٩)`), and words such as التقدم / متقدم / يتقدم.
- Page-based and name-based backward references could be resolved once units carry page/subject indexes (T-071/T-080); left unresolved for review here.
