---
id: T-084
title: "Inferred relations from headings (assertion=inferred)"
epic: E08
priority: P1
depends_on: [T-073, T-083]
estimate: S
owner: agent
status: done
wave: 13
---

# T-084 — Inferred relations from headings (assertion=inferred)

**Epic:** E08 Entities & relationships · **Priority:** P1 · **Estimate:** S · **Wave:** 13

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
'أولاد رسول الله' heading implies child_of Prophet for entries 1–4 — this is NOT stated in each entry, so it is ai_generated + inferred with the heading as evidence.

## Scope
- From section_subject + heading phrase create relations with `assertion:'inferred'`, `origin:'ai_generated'`, evidence anchors = heading block + entry block.
- Inferred relations involving the Prophet → sensitive `prophetic_attribution`? NO (genealogy) — but always `pending_review` in MVP (config `review.inferred_always_review: true`).

## Files
- `src/ilm_engine/extractors/relations.py`
- `tests/test_inferred_relations.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] child_of(فاطمة #1, ent_prophet) exists with assertion 'inferred', evidence [b000104, b000105].
- [x] No inferred relation is auto_approved.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_inferred_relations.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `inferred_relations(book, units, relations, config)`: for each section with a subject (T-073) every entry gets `child_of` the subject (the Prophet maps to `ent_prophet`; another subject reuses an entity with the exact normalized name, else a new one); a heading with "من أمهم X" (Khadija section #8–#10) gives `sibling_of` kind `maternal` to every child listed under the same subject without a mother clause. All are `assertion: inferred`, `origin: ai_generated`, LLM-level confidence, evidence = heading anchor + entry anchor (Fatimah: [b000104, b000105]).
- New config key `review.inferred_always_review: true` (default): inferred relations are always `pending_review`, never auto-approved. They are not tagged `prophetic_attribution` (genealogy, not a Prophetic statement), as the ticket specifies.
- A stated parent from a closure phrase outranks the heading: no inferred `child_of` is added for an entry that already has a stated one (e.g. #18–#21 "بنو عبد المطلب").
