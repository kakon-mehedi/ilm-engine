---
id: T-140
title: "Step registry & DAG runner (cached, idempotent)"
epic: E14
priority: P0
depends_on: [T-002, T-003, T-020]
estimate: M
owner: agent
status: done
wave: 2
---

# T-140 — Step registry & DAG runner (cached, idempotent)

**Epic:** E14 Pipeline runner & CLI · **Priority:** P0 · **Estimate:** M · **Wave:** 2

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
MVP orchestration mirrors Prefect: named steps, declared inputs/outputs, retries, cache by input hash, so the move to Prefect is 1:1.

## Scope
- `pipeline/steps.py`: `@step(name, needs=[...], outputs=[...])`; `pipeline/runner.py` topological run, cache key = sha256(step code version + config_hash + input hashes), skip if cached outputs exist.
- Steps registered in this exact order (DECISIONS §12b): `ingest` → `adapt` → `integrity_register` → `document_analysis` → `structure` → `origin` → `metadata` → `genre` → `annotations` → `citations` → `related_works` → `units` → `entities` → `relations` → `search_index` → `validate` → `review_queue` → `store` → `export` → `integrity_verify` → `manifest`. Document in `pipeline/README.md` how they map to the assignment's 12 data-flow steps.
- `--only <step>`, `--from <step>`, `--no-cache`.

## Files
- `src/ilm_engine/pipeline/steps.py`
- `src/ilm_engine/pipeline/runner.py`
- `tests/test_runner.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] Second run with no changes executes 0 steps (all cached).
- [x] Changing config threshold re-runs only validation+downstream steps.
- [x] `ilm-engine run --list-steps` prints the 21 step names in the order above.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_runner.py -q
```

## Out of scope
- Prefect (T-160).

## Follow-ups
- The cache key covers only the config sections a step declares (`Step.config`), not the whole config hash; otherwise any config change would re-run every step and the criterion "a threshold change re-runs only validation and downstream" could not hold. The full `config_hash` still goes into the run manifest (T-141).
- A cache hit also requires the step's output files to exist with their recorded hashes; a deleted or edited output re-runs that step. Cached results (in-memory data + issues) are pickled under `.cache/steps/<step>/<key>.pkl`; this is a local cache written only by the runner.
- Steps are registered with placeholder functions (reported `skipped`); each later ticket attaches its implementation with `PIPELINE.replace(name, fn)`. Dependencies follow 02-architecture §4.
- `ilm-engine run` gained `--list-steps`, `--only`, `--from`, `--no-cache`, `--input` and `--out`; T-142 completes the CLI (`--llm`, `--pdf`, other commands).
- `pipeline/README.md` maps the steps to the assignment's 12 data-flow steps.
