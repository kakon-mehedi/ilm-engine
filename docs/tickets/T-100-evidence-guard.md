---
id: T-100
title: "Evidence guard (hallucination guard)"
epic: E10
priority: P0
depends_on: [T-060]
estimate: S
owner: agent
status: done
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
- [x] locate('أسلمت', b000135) → (60,65), factor 1.0.
- [x] locate('اسلمت', b000135) → (60,65), factor 0.9.
- [x] locate('ولد في مكة', b000135) → None.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_evidence.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `locate(quote, block, *, pub_ref, scan_page, hint_start=None) -> EvidenceMatch | None`; `EvidenceMatch{anchor, match, factor, occurrences, ambiguity_penalty}`. `Block` has no scan page, so callers pass it (from `Page.scan_page`).
- Normalized matching tries the milder `match` profile first, then `search`; both give factor 0.9 (also covers NFC-only differences, EC-066). The anchor's `quote` is always the original text at the mapped offsets.
- Several occurrences: nearest to `hint_start`; without a hint the first one with `ambiguity_penalty` 0.9 (ADR-007 §3).
- Added `anchor_status(anchor, block)` → valid / stale / orphaned (ADR-017), for T-023 and integrity_verify.
