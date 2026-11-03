---
id: T-015
title: "Adapter authoring guide + example OCR-team v1 adapter"
epic: E01
priority: P1
depends_on: [T-014]
estimate: M
owner: agent
status: todo
wave: 5
---

# T-015 — Adapter authoring guide + example OCR-team v1 adapter

**Epic:** E01 Canonical model + adapters · **Priority:** P1 · **Estimate:** M · **Wave:** 5

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Show that a different JSON format (e.g. future output of the OCR team) plugs in by adding one adapter.

## Scope
- Define a hypothetical `ocr-team v1` format in `tests/golden/ocr_team_v1/input.json` (pages → lines with bbox, footnotes as separate list, no refs).
- `adapters/ocr_team_v1.py` mapping it to canonical (refs empty; marker detection deferred → issue `unlinked_footnote` later).
- `docs/ADAPTERS.md`: step-by-step guide (detect, map, golden test, register, version bump rules).

## Files
- `src/ilm_engine/adapters/ocr_team_v1.py`
- `tests/golden/ocr_team_v1/*`
- `docs/ADAPTERS.md`
- `tests/test_ocr_team_v1.py`

## Implementation notes
- Bbox is kept in `raw_extras` until a canonical field is approved (ADR).

## Acceptance criteria
- [ ] Registry resolves both adapters correctly for their inputs.
- [ ] Pipeline steps E03 run on the OCR-team sample without code changes (may produce issues, must not crash).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_ocr_team_v1.py -q
```

## Out of scope
- Real OCR.
