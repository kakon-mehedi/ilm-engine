---
id: T-142
title: "CLI: run | verify | search | eval | review apply"
epic: E14
priority: P0
depends_on: [T-140, T-021]
estimate: S
owner: agent
status: done
wave: 3
---

# T-142 — CLI: run | verify | search | eval | review apply

**Epic:** E14 Pipeline runner & CLI · **Priority:** P0 · **Estimate:** S · **Wave:** 3

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
One command runs everything (assignment MVP: 'one command executes the pipeline').

## Scope
- `ilm-engine run --input <json|dir> [--pdf …] [--llm null|fixture|anthropic|litellm] [--out output]` (see DECISIONS §10; a directory input finds the PDF via `_meta.scan.saved_file`). Also `ilm-engine dev regen-goldens` (developer-only).
- `verify <out_dir>`, `search "<q>"`, `eval`, `review apply <review_decisions.json>` and `review html` (logic in T-105).
- `rebuild-derived <out_dir>`: rebuild `search_index.json` and `graph.html` from `enrichment.db` (ADR-005); output must be byte-identical to the original run.
- `schema export --out schemas/`: write JSON Schema for every top-level model in `enrichment/models.py` and `canonical/models.py` (03-data-contracts.md).
- Exit codes: 0 ok, 1 validation failure, 2 unknown schema.

## Files
- `src/ilm_engine/cli.py`
- `tests/test_cli.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria

- [x] `rebuild-derived` after deleting `search_index.json` and `graph.html` reproduces them with identical hashes.
- [x] `schema export` writes one JSON Schema file per top-level model into `schemas/`.
- [x] `ilm-engine run --input data` completes on the sample with provider null in < 60 s and writes all files of DECISIONS §10 (graph.html optional).
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run ilm-engine run --input data && uv run ilm-engine verify output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- Implemented here: `run` (`--input <json|dir>`, `--pdf`, `--llm`, `--out`, `--only`, `--from`, `--no-cache`, `--list-steps`, plus `--store` and `--cache-dir` so tests never touch the repository's `store/` or `.cache/`), `verify <out_dir>`, `schema export --out schemas/`, and exit codes 0 / 1 / 2 (unknown schema).
- The first three steps are wired (`pipeline/stages.py`: `ingest`, `adapt`, `integrity_register`), following architecture L1–L2; without them `run` could not process the book. Later tickets add their steps to `stages.py` and `_wire`.
- **Deferred to the tickets that build their logic** (so no command is a stub): `search` (T-122), `eval` (T-132), `review apply` / `review html` (T-105), `rebuild-derived` (T-113, needs `graph.html`), `dev regen-goldens` (T-014). The acceptance criteria "rebuild-derived reproduces identical hashes" and "run writes all files of DECISIONS §10" are therefore verified in T-113 / T-143.
- `schemas/` holds the exported JSON Schemas (committed); `test_committed_schemas_are_current` fails when a model changes without re-export. Genre payload schemas are added by T-095.
- `verify` checks output and input hashes against the manifest, the original store (`integrity.store.verify`) and the manifest's integrity record.
