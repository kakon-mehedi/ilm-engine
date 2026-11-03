---
id: T-084
title: "Inferred relations from headings (assertion=inferred)"
epic: E08
priority: P1
depends_on: [T-073, T-083]
estimate: S
owner: agent
status: todo
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
- [ ] child_of(فاطمة #1, ent_prophet) exists with assertion 'inferred', evidence [b000104, b000105].
- [ ] No inferred relation is auto_approved.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_inferred_relations.py -q
```

## Out of scope
- Anything not listed in Scope.
