---
id: T-142
title: "CLI: run | verify | search | eval | review apply"
epic: E14
priority: P0
depends_on: [T-140, T-021]
estimate: S
owner: agent
status: todo
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

- [ ] `rebuild-derived` after deleting `search_index.json` and `graph.html` reproduces them with identical hashes.
- [ ] `schema export` writes one JSON Schema file per top-level model into `schemas/`.
- [ ] `ilm-engine run --input data` completes on the sample with provider null in < 60 s and writes all files of DECISIONS §10 (graph.html optional).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run ilm-engine run --input data && uv run ilm-engine verify output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6
```

## Out of scope
- Anything not listed in Scope.
