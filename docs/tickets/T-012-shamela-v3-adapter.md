---
id: T-012
title: "ShamelaV3Adapter (src-shamela, af_schema 3.0)"
epic: E01
priority: P0
depends_on: [T-011, T-020]
estimate: M
owner: agent
status: todo
wave: 3
---

# T-012 — ShamelaV3Adapter (src-shamela, af_schema 3.0)

**Epic:** E01 Canonical model + adapters · **Priority:** P0 · **Estimate:** M · **Wave:** 3

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Convert the provided archive JSON into `CanonicalBook`. Source is Shamela, NOT OCR.

## Scope
- Map `pub`, `revision`, `work`, `editions`, `metadata` → `book_ref`, `source`, `metadata_raw`, `toc` (from `metadata.source_attributes.toc`).
- Map `content.pages[]` → `Page` (n, volume, scan_page, `source_ref.key` → `source_key`, `source_ref.url`).
- Map every block → `Block` with `page`, global `order`, `block_hash` (T-020).
- `declared_content_hash = content.content_sha256`.
- `adapter_version = '1.0.0'`; `schema_versions = {'3.0'}`; `source_code = 'src-shamela'`.

## Files
- `src/ilm_engine/adapters/shamela_v3.py`
- `tests/test_shamela_v3.py`

## Implementation notes
- Spans keep their `class` as `cls` verbatim (c1, c2, c4, c5); do not interpret here.
- PDF path is stored only as reference; no PDF parsing (no text layer).

## Acceptance criteria
- [ ] Sample → 68 pages, `n` from 3 to 72, 594 blocks (text 260, footnote 317, heading 15, toc_heading 2).
- [ ] Total refs = 300; 16 blocks have `continues=True`; 17 TOC entries.
- [ ] `book_ref.pub_ref == 'pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6'`.
- [ ] `book.block('b000135').text[60:65] == 'أسلمت'` and `len(text) == 102`.
- [ ] Input dict is not mutated (deep-compare before/after).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_shamela_v3.py -q
```

## Out of scope
- Interpreting refs/footnotes (E05).
