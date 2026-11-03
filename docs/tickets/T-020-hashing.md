---
id: T-020
title: "Hashing utilities (block hash, canonical content hash)"
epic: E02
priority: P0
depends_on: [T-001]
estimate: S
owner: agent
status: todo
wave: 1
---

# T-020 — Hashing utilities (block hash, canonical content hash)

**Epic:** E02 Integrity · **Priority:** P0 · **Estimate:** S · **Wave:** 1

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Integrity is proved with hashes (Section 6: original content untouched).

## Scope
- `block_hash(text) -> 'sha256:<hex>'` over exact UTF-8 bytes.
- `canonical_json(obj) -> bytes` (`sort_keys=True, separators=(',',':'), ensure_ascii=False`).
- `content_hash(book) -> 'sha256:…'` over canonical JSON of `[ (id, kind, text, marker, refs) for blocks in order ]`.
- `file_sha256(path)`.

## Files
- `src/ilm_engine/integrity/hashing.py`
- `tests/test_hashing.py`

## Implementation notes
- Declared Shamela `content_sha256` is NOT reproducible by us → stored with issue `source_hash_unverified` (T-021).

## Acceptance criteria
- [ ] Hash of 'أسلمت' is stable and differs from its normalized form 'اسلمت'.
- [ ] `content_hash` identical across two adapter runs.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_hashing.py -q
```

## Out of scope
- Anything not listed in Scope.
