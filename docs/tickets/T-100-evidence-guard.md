---
id: T-100
title: "Evidence guard (hallucination guard)"
epic: E10
priority: P0
depends_on: [T-060]
estimate: S
owner: agent
status: todo
wave: 2
---

# T-100 — Evidence guard (hallucination guard)

**Epic:** E10 Validation & human review · **Priority:** P0 · **Estimate:** S · **Wave:** 2

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
A fact is valid only if its quote exists in the cited block. This is the core traceability guarantee.

## Scope
- `validation/evidence.py`: `locate(quote, block) -> Anchor|None`: exact find → evidence 1.0; else normalized find via index map → 0.9 and anchor mapped back to original offsets; else None (evidence 0).
- Multiple occurrences → choose nearest to hint offset; record `occurrences`.

## Files
- `src/ilm_engine/validation/evidence.py`
- `tests/test_evidence.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] locate('أسلمت', b000135) → (60,65), factor 1.0.
- [ ] locate('اسلمت', b000135) → (60,65), factor 0.9.
- [ ] locate('ولد في مكة', b000135) → None.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_evidence.py -q
```

## Out of scope
- Anything not listed in Scope.
