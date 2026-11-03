---
id: T-010
title: "Canonical book models (canonical/models.py)"
epic: E01
priority: P0
depends_on: [T-001]
estimate: M
owner: agent
status: todo
wave: 1
---

# T-010 — Canonical book models (canonical/models.py)

**Epic:** E01 Canonical model + adapters · **Priority:** P0 · **Estimate:** M · **Wave:** 1

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Every source format is converted into ONE internal shape. Downstream code only ever sees the canonical model (ADR: adapter + canonical schema).

## Scope
- **Authoritative spec:** implement `docs/03-data-contracts.md` §1–2 exactly (field names there win over the summary below). Also create `src/ilm_engine/enrichment/models.py` with all enrichment models of §3–18 (Anchor, Issue, …, RunManifest) so later tickets import them instead of redefining.
- Pydantic models: `CanonicalBook{canonical_schema_version='1.0', book_ref{pub_id, revision, pub_ref, work_id, edition_id}, source{code, book_key, schema_version, adapter, adapter_version, source_declared_hash, source_declared_hash_verified}, metadata_raw: dict, toc: list[TocEntry], pages: list[Page], raw_extras: dict}`.
- `Page{volume, n, scan_page, source_key, source_url, block_ids: list[str]}`.
- `Block{id, page, order, kind: Literal['text','heading','toc_heading','footnote'], text, marker: str|None, continues: bool, spans: list[Span], refs: list[Ref], block_hash}`; `Span{cls, start, end, text}`; `Ref{start, end, to}`; `TocEntry{title, source_page, depth}`.
- Models are frozen (immutable) — original text can never be mutated in memory.
- Helper `book.block(id)`, `book.blocks_in_order()`, `book.page(n)`.

## Files
- `src/ilm_engine/enrichment/models.py`
- `src/ilm_engine/canonical/models.py`
- `tests/test_canonical_models.py`

## Implementation notes
- `order` = global reading order index (0..593).
- No normalization of text here — exact source text.

## Acceptance criteria
- [ ] Models are frozen: assigning `block.text = 'x'` raises.
- [ ] Round-trip `model_dump_json()` → `model_validate_json()` is lossless.
- [ ] `Block.kind` rejects unknown kinds.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_canonical_models.py -q
```

## Out of scope
- Parsing the Shamela JSON (T-012).
