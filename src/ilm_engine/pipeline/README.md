# Pipeline steps

`steps.py` registers 21 steps in execution order (DECISIONS §12b); `runner.py` runs them as an
in-process DAG with per-step caching (ADR-004). In production each step becomes one Prefect task.

## Mapping to the assignment's 12 data-flow steps

| Assignment step | Pipeline steps |
|---|---|
| 1. Receive digitized text, PDF and identifiers | `ingest` → `adapt` → `integrity_register` |
| 2. Analyse document structure | `document_analysis`, `structure`, `origin` |
| 3. Extract and enrich metadata | `metadata` |
| 4. Identify genre and related works | `genre`, `related_works` |
| 5. Structural and semantic indexes | `structure`, `search_index` |
| 6. Identify and map annotations and references | `annotations`, `citations` |
| 7. Extract genre-specific knowledge units | `units` |
| 8. Identify entities and relationships | `entities`, `relations` |
| 9. Validate with AI-based quality checks | `validate` |
| 10. Send uncertain or sensitive results to human review | `review_queue` |
| 11. Store approved information in the enrichment layer | `store` |
| 12. Make enriched books available for publishing and search | `export` |
| (integrity and provenance) | `integrity_verify`, `manifest` |

Execution order differs from the assignment's numbering where a step needs another's output:
`related_works` (4) runs after `citations` (6), and `search_index` (5) after `relations` (8).

## Caching

A step's cache key is `sha256(name + version + config sections it reads + upstream cache keys + input
file hashes)`. Changing `review.threshold.default`, for example, changes the keys of `validate` and
`review_queue` only, so those steps and everything downstream re-run while earlier steps are reused.
Options: `--only <step>` (that step, reusing cached upstream steps), `--from <step>` (re-run the step
and everything downstream), `--no-cache` (re-run everything).
