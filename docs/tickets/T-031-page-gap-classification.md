---
id: T-031
title: "Missing-page detection and classification"
epic: E03
priority: P1
depends_on: [T-030]
estimate: S
owner: agent
status: todo
wave: 5
---

# T-031 — Missing-page detection and classification

**Epic:** E03 Document analysis, structure, origin · **Priority:** P1 · **Estimate:** S · **Wave:** 5

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Missing pages are not automatically missing content. Pages 1, 2, 4, 18 are cover, publisher page, basmala, blank.

## Scope
- Detect missing page numbers in 1..max(n) → issue `missing_page` each.
- Classification via per-book override `page_gaps: {1: cover, 2: publisher_page, 4: basmala, 18: blank}` with `evidence: scan_page`.
- Pages without override → `unknown` and severity `warning`.
- Report PDF extra pages 73–80 as `printed_indexes` (from override).

## Files
- `src/ilm_engine/processors/document_analysis.py`
- `config/books/pub_01M0CJECV4ZHFTP02BJQ6D3STJ.yaml`
- `tests/test_page_gaps.py`

## Implementation notes
- Without override the system must still report gaps, just unclassified.

## Acceptance criteria
- [ ] Missing pages exactly [1, 2, 4, 18], each classified as in override.
- [ ] `page_count_mismatch` downgraded to `info` with explanation 'no content pages missing'.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_page_gaps.py -q
```

## Out of scope
- Looking at the PDF automatically (no text layer).
