---
id: T-141
title: "Run manifest (provenance of a run)"
epic: E14
priority: P0
depends_on: [T-140]
estimate: S
owner: agent
status: done
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
- [x] Manifest lists every output file with sha256; input hash of the sample JSON present.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_manifest.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `run_id = make_id("run", pub_ref, config_hash | input hashes | code version)` (ADR-011 natural key), so reruns of the same code, config and input share it; timestamps live only in the manifest.
- `code_version` is the git SHA, or `dirty-<sha12>-<diff hash12>` when tracked files have uncommitted changes.
- Steps contribute `adapter`, `counts` and `integrity` through `StepResult.data`; the manifest merges them. Output hashes cover every file in `output/<pub_ref>/` except the manifest itself.
- `RunContext` gained `records` (steps finished so far, set by the runner) and `started_at`. The manifest step is wired into `PIPELINE`; it is skipped until `adapt` sets `pub_ref`.
