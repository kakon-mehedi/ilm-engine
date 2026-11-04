---
id: T-073
title: "Section membership and group headings"
epic: E07
priority: P1
depends_on: [T-071]
estimate: S
owner: agent
status: done
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
- [x] Units under '* الأُخوة من ولد العباس بن عبد المطلب:' (b000339) get section_subject 'العباس بن عبد المطلب'.
- [x] Units under 'أولاد رسول الله' (b000104) get subject 'رسول الله ﷺ'.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_section_membership.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `section_subject(title) -> (subject, mother)`: the person after أولاد / ولد / ذرية / بنو in the heading, bounded by the nasab parser (so "؛ وكان أكبر ولد أبيه" is cut off), diacritics removed; "رسول الله -صلى الله عليه وسلم-" → "رسول الله ﷺ"; "من أمهم خديجة" → mother "خديجة".
- Stored in the unit payload (biography schema gained `section_subject`, `section_mother`, `section_heading_anchor`; schemas re-exported): b000339 → "العباس بن عبد المطلب", b000104 → "رسول الله ﷺ", Khadija section → subject "رسول الله ﷺ", mother "خديجة". The whole heading is the anchor that T-084's inferred relations cite.
- `section_id` itself was attached in T-071.
