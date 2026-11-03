---
id: T-110
title: "JSON enrichment store"
epic: E11
priority: P0
depends_on: [T-003]
estimate: S
owner: agent
status: todo
wave: 2
---

# T-110 — JSON enrichment store

**Epic:** E11 Enrichment storage & export · **Priority:** P0 · **Estimate:** S · **Wave:** 2

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Approved/pending enrichment is stored separately from originals (Section 6).

## Scope
- `storage/json_store.py` writes each output file of DECISIONS §10 under `output/<pub_ref>/` using canonical JSON (sorted keys, UTF-8, indent 2).
- Atomic writes (tmp + rename). Refuses any path under `data/` or `store/originals/`.

## Files
- `src/ilm_engine/storage/json_store.py`
- `tests/test_json_store.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Writing to `data/x.json` raises.
- [ ] Two writes of the same object produce byte-identical files.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_json_store.py -q
```

## Out of scope
- Anything not listed in Scope.
