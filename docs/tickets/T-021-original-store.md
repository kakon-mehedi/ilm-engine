---
id: T-021
title: "Read-only original store"
epic: E02
priority: P0
depends_on: [T-020]
estimate: S
owner: agent
status: todo
wave: 2
---

# T-021 — Read-only original store

**Epic:** E02 Integrity · **Priority:** P0 · **Estimate:** S · **Wave:** 2

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Originals are copied once into a content-addressed store and never written again; the pipeline reads only from there.

## Scope
- `integrity/store.py`: `ingest(json_path, pdf_path, pub_ref) -> StoredOriginal` copying to `store/originals/<pub_ref>/` with `manifest.json` (file hashes, declared hash, ingest time).
- Set files read-only (chmod 0o444).
- `verify(pub_ref) -> bool` re-hashes files.
- Emit issue `source_hash_unverified` when declared hash cannot be reproduced.

## Files
- `src/ilm_engine/integrity/store.py`
- `tests/test_store.py`

## Implementation notes
- Never touch `data/` (only read).

## Acceptance criteria
- [ ] After ingest, files are mode 0444 and `verify()` returns True.
- [ ] Modifying a stored copy (in a tmp test) makes `verify()` False.
- [ ] Hash of `data/demo_book_daraqutni.json` unchanged after ingest.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_store.py -q
```

## Out of scope
- MinIO/S3 (production).
