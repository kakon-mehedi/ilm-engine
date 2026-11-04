---
id: T-015
title: "Adapter authoring guide + example OCR-team v1 adapter"
epic: E01
priority: P1
depends_on: [T-014]
estimate: M
owner: agent
status: done
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
- [x] Registry resolves both adapters correctly for their inputs.
- [x] Pipeline steps E03 run on the OCR-team sample without code changes (may produce issues, must not crash).
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_ocr_team_v1.py -q
```

## Out of scope
- Real OCR.

## Follow-ups
- The OCR-team v1 sample is synthetic (invented short Arabic lines), so its golden files are committed, unlike the Shamela excerpt.
- The format declares no `pub.source_code` / `metadata.af_schema`; the registry resolves it through `detect()` (`format == "ocr-team"`, major version 1). Lines → text/heading blocks, per-page footnote list → footnote blocks with their marker, no refs (linking is left to the annotation step). Bounding boxes and any other extra keys stay in `raw_extras`.
- E03 steps (document analysis, structure, origin) run on it unchanged; the gap at page 3 is reported as `missing_page`.
- `docs/ADAPTERS.md`: recognition order, mapping rules, registration, golden tests, version-bump rules.
