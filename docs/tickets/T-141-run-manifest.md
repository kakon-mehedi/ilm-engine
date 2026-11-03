---
id: T-141
title: "Run manifest (provenance of a run)"
epic: E14
priority: P0
depends_on: [T-140]
estimate: S
owner: agent
status: todo
wave: 3
---

# T-141 — Run manifest (provenance of a run)

**Epic:** E14 Pipeline runner & CLI · **Priority:** P0 · **Estimate:** S · **Wave:** 3

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Repeatability and audit: what code, config, models and inputs produced these outputs.

## Scope
- `run_manifest.json` per DECISIONS §10: run_id, timestamps, git sha, config_hash, canonical schema version, adapter+version, models+prompt versions, input file hashes, output file hashes, step timings, cache hits.

## Files
- `src/ilm_engine/pipeline/manifest.py`
- `tests/test_manifest.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Manifest lists every output file with sha256; input hash of the sample JSON present.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_manifest.py -q
```

## Out of scope
- Anything not listed in Scope.
