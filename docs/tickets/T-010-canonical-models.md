---
id: T-010
title: "Canonical book models (canonical/models.py)"
epic: E01
priority: P0
depends_on: [T-001]
estimate: M
owner: agent
status: done
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
- [x] Models are frozen: assigning `block.text = 'x'` raises.
- [x] Round-trip `model_dump_json()` → `model_validate_json()` is lossless.
- [x] `Block.kind` rejects unknown kinds.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_canonical_models.py -q
```

## Out of scope
- Parsing the Shamela JSON (T-012).

## Follow-ups
- Implemented `03-data-contracts.md` §1–2 and §3–18 as written; contract names win over the summary above (`Block.block_id`, `TocEntry.source_page_key`, `BookRef.source_work_id`, `Page.source_key`, …).
- `Strict` and `BlockKind` live in `canonical/models.py` (the base layer); `enrichment/models.py` imports them.
- Contract names that clash with Python/Pydantic use aliases and serialize by alias: `Span.cls` ↔ `"class"`, `ConfidenceFactors.schema_` ↔ `"schema"`.
- Invariants enforced in the models: span/ref offsets inside the block text and span text equal to the slice (all 594 sample blocks pass); `pub_ref == pub_id@r<revision>`; block order 0..N-1; page block IDs exist; no duplicate pages; anchor `start <= end`; `block_hash` / `canonical_content_hash` are `sha256:<64 hex>`; confidence in [0, 1]; facts and relationships carry ≥1 evidence anchor; `assertion: inferred` requires `origin: ai_generated` (ADR-010); sensitive review items require `scholar_reviewer` (DECISIONS §12c); our `Work.work_id` is `wrk_<12 hex>`.
- `PersonName.ism/kunya/laqab` default to `None` so the contract's own examples (which omit them) validate.
- Added `Structure`, `EnrichmentSource` and `Enrichment` for the §18 consolidated file.
- Genre payload models (§12) are left to T-095 (genre plugin schemas).
- **Doc fix needed:** the b000135 text in `03-data-contracts.md` (§2 block example, §11 unit anchor) has the diacritics of "اللَّه" in the wrong order (fatha before shadda; the source has shadda before fatha). It looks identical but does not hash to the stated `block_hash`. Tests use the exact source text.
