# ADR-011: Deterministic IDs and repeatable runs

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§6 requires processing that is "modular, repeatable and scalable". Repeatability matters for three reasons:
- reviewers' decisions must still attach to the same item after a rerun;
- comparing two runs (new prompt, new model) needs stable keys;
- reprocessing one book after a source revision must not duplicate records.

Random UUIDs, wall-clock-dependent ordering and non-zero LLM temperature all break repeatability.

## Decision

- **IDs:** `<prefix>_<first 12 hex chars of sha256(pub_ref + "|" + natural_key)>`, generated in `ids.py`. Prefixes are `sec, ku, ent, rel, ann, cit, wrk, iss, rev, run`. Natural keys:
  - section: `toc_index|first_block_id`
  - knowledge unit: `entry_no|block_id|start`
  - annotation: `source_block|start|target_block`
  - citation: `block_id|start|normalized_title`
  - entity: `normalized_canonical_name|first_anchor`
  - relationship: `type|subject_id|object_id`
  - issue: `code|target`
  - review item: `target_id|reason`
  - run: `config_hash|input_hash|code_version`
- Source IDs (`b000135`, `pub_…`, `wrk_01M0…`) are kept as they are and never renumbered. Our `wrk_` IDs are 12 lowercase hex characters, which keeps them distinct from source work IDs (26 uppercase Crockford characters).
- **Run manifest:** `run_manifest.json` records the run_id, the code version (git sha), config hash, canonical schema version, adapter id and version, model ids and prompt versions, input file hashes and output file hashes.
- **Deterministic execution:** sorted iteration (by page, then block order, then offset); JSON written with `sort_keys=True` and stable list order; LLM temperature 0 plus the response cache (ADR-006); no timestamps inside content files (timestamps only in the manifest).
- **Idempotent steps:** a rerun with the same inputs reproduces identical outputs and IDs (ADR-004 cache).
- **Incremental reprocessing:** when a new revision arrives, blocks are compared by `block_hash`. Unchanged blocks keep their enrichment IDs, and only changed blocks are reprocessed (ADR-017).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Content-derived hash IDs + manifest (chosen)** | Stable across reruns; no ID service; diffable | Natural keys must be chosen carefully |
| B. UUID4 | Simple | New IDs every run; reviews detach |
| C. Database sequences | Compact | Order-dependent; differ across environments |
| D. ULID (time-based) | Sortable | Time-dependent, not reproducible |

## Consequences

- **+** Two runs can be diffed file by file; review decisions survive reruns.
- **−** Changing a natural-key definition changes IDs. That is a breaking change and needs a migration note in the ADR.
- **−** Very rarely, two different records could collide on 12 hex characters. Collisions are checked per run, and the ID is extended to 16 characters if one occurs.

## Compliance / how verified

- Test: run the pipeline twice. All output hashes are equal, and `run_manifest.json` differs only in timestamps and run_id.
- Test: no duplicate IDs within any output file.

## Related

ADR-004, ADR-006, ADR-017.
