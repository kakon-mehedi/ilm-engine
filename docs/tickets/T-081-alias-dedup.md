---
id: T-081
title: "Alias resolution and de-duplication"
epic: E08
priority: P1
depends_on: [T-080]
estimate: M
owner: agent
status: done
wave: 11
---

# T-081 — Alias resolution and de-duplication

**Epic:** E08 Entities & relationships · **Priority:** P1 · **Estimate:** M · **Wave:** 11

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Same person appears under different surface forms (الدارقطني / أبو الحسن الدارقطني / علي بن عمر الدارقطني).

## Scope
- Merge candidates by normalized (ism + chain prefix ≥2) or nisba+kunya match; produce `aliases`.
- Same ism but conflicting chains → keep separate + issue `ambiguous_entity` (sensitive `narrator_disambiguation` when the person is a narrator).

## Files
- `src/ilm_engine/extractors/entities.py`
- `tests/test_alias.py`

## Implementation notes
- Never merge on ism alone.

## Acceptance criteria
- [x] Al-Daraqutni mentions (b000004, b000043, card) merge into one entity with ≥3 aliases.
- [x] Hind #8 and Hind #9 stay separate.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_alias.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- Merge rule (`same_person`): same ism with ≥ 2 shared chain names, or same kunya and nisba; never the ism alone (Hind #8 and the elliptic Hind #9 stay separate).
- Full-name mentions in the front matter (pages ≤ 19) are found by "ism بن first ancestor" on the normalized text and parsed: the author entity gets b000004, b000043 (long chain "… بن مهدي بن مسعود …") and b000083 (p.17, "بن مهدي") as mentions and their surfaces as aliases.
- A bare nisba ("الدارقطني", "الدَّارقطني", "الدارقطنى") is added as an alias/mention only when exactly one entity in the book carries that nisba (here the author); up to 20 such mentions.
- People sharing an ism whose chains start with the same ancestor but then conflict are kept separate, marked `disambiguation: ambiguous` with `candidates`, and raise `ambiguous_entity` (validation adds `narrator_disambiguation`, so they go to scholar review). None on the sample.
- Aliases are stored sorted.
