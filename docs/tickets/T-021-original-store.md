---
id: T-021
title: "Read-only original store"
epic: E02
priority: P0
depends_on: [T-020]
estimate: S
owner: agent
status: done
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
- [x] After ingest, files are mode 0444 and `verify()` returns True.
- [x] Modifying a stored copy (in a tmp test) makes `verify()` False.
- [x] Hash of `data/demo_book_daraqutni.json` unchanged after ingest.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_store.py -q
```

## Out of scope
- MinIO/S3 (production).

## Follow-ups
- `ingest(json_path, pdf_path, pub_ref, declared_hash=None, store_root=store/originals)`: the declared hash is passed in by the caller (the adapter knows where the source keeps it), so the store stays format-agnostic. It counts as verified only if it equals the sha256 of a stored file's bytes; otherwise `StoredOriginal.issues` holds `source_hash_unverified` (info).
- Immutability: re-ingesting identical files returns the existing entry without rewriting anything; different files for the same `pub_ref` raise `OriginalStoreError`. `manifest.json` is read-only too.
- `verify` also fails if a stored file became writable or is missing.
