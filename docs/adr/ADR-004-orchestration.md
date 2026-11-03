# ADR-004: Orchestration — in-process DAG runner (MVP), Prefect (production), no Celery

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§3.3 asks for "Python scripts, workflow orchestration, AI agents and task-specific pipelines". The pipeline is a DAG of 21 steps per book. The step names are fixed in DECISIONS.md §12b:
`ingest` → `adapt` → `integrity_register` → `document_analysis` → `structure` → `origin` → `metadata` → `genre` → `annotations` → `citations` → `related_works` → `units` → `entities` → `relations` → `search_index` → `validate` → `review_queue` → `store` → `export` → `integrity_verify` → `manifest`.

Production will process thousands of books. That means long-running LLM calls, retries, rate limits, and partial reruns when a source revision changes.

A typical stack lists both an orchestrator (Temporal / Prefect) and a task queue (Celery + Redis). An orchestrator already provides queuing, retries and scheduling, so having both duplicates responsibility.

The MVP must run on a laptop with one command and no services.

## Decision

- **MVP:** a small in-process DAG runner (`pipeline/runner.py`). Each step is a pure function `step(inputs, config) -> outputs`, declared with its dependencies in `pipeline/steps.py`. The runner:
  - runs steps in topological order;
  - computes the cache key `sha256(step_name + step_version + input hashes + config hash)` and skips a step whose cached output already exists;
  - writes `run_manifest.json` (ADR-011).
- **Production:** Prefect. Each MVP step maps 1:1 to a Prefect task, and one book is one flow run. Rate-limited LLM tasks use Prefect concurrency limits. Work pools scale workers horizontally.
- **No Celery or Redis.**

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. In-process runner now, Prefect later (chosen)** | Zero infrastructure for the MVP; same step contract; Python-native; good UI, retries and caching | Two runners to keep compatible (thin adapter) |
| B. Temporal | Strongest durability for very long workflows | Heavier operations (server, workers, SDK model); overkill for book batches |
| C. Airflow | Mature and common | Schedule-centric DAGs; awkward for per-book dynamic fan-out; heavy for the MVP |
| D. Celery + Redis | Simple task queue | No DAG or lineage view; retries and dependencies are hand-built; duplicates the orchestrator |
| E. Plain script without caching | Simplest | Not repeatable or resumable; every rerun pays LLM costs again |

## Consequences

- **+** Steps are idempotent and cacheable from day one, so moving to Prefect is mechanical.
- **+** Partial reruns (one step, one book, one revision) are possible.
- **−** The in-process runner has no distributed execution. That is acceptable for one sample book.
- **−** If a workflow ever needs to wait days for a human inside one run, Temporal may be revisited. In this design, review happens outside the run, so this is unlikely.

## Compliance / how verified

- Test: running `ilm-engine run` twice gives identical output hashes, and the second run reports every step as `cached`.
- Test: changing one config value invalidates only the steps that read it.
- An E16 ticket describes the Prefect flow mapping.

## Related

ADR-005, ADR-011.
