---
id: T-030
title: "Document analysis report (quality & stats)"
epic: E03
priority: P0
depends_on: [T-012]
estimate: S
owner: agent
status: todo
wave: 4
---

# T-030 — Document analysis report (quality & stats)

**Epic:** E03 Document analysis, structure, origin · **Priority:** P0 · **Estimate:** S · **Wave:** 4

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Data-flow step 2: understand the document before enriching it.

## Scope
- `processors/document_analysis.py` → `document_report.json`: block counts by kind, pages present, page range, declared vs held page count, empty/duplicate blocks, refs total/resolved, continued footnotes, span class counts.
- Re-evaluate the source quality record: claimed 72, held 68, short 5.6% vs tolerance 5% but `passed: true` → issue `page_count_mismatch` with note.

## Files
- `src/ilm_engine/processors/document_analysis.py`
- `tests/test_document_analysis.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Report: 594 blocks; text 260, footnote 317, heading 15, toc_heading 2; 68 pages; refs 300/300 resolvable; 16 continued footnotes; spans c2 230, c5 64, c1 8, c4 2.
- [ ] Issue `page_count_mismatch` present with claimed 72 / held 68.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_document_analysis.py -q
```

## Out of scope
- Anything not listed in Scope.
