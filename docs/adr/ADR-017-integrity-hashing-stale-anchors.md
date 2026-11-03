# ADR-017: Integrity hashing and stale anchors

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§6 requires that the original content remains untouched and that enrichment stays linked to it. We need to prove two things:
1. our system never modified the original;
2. every anchor still points at the text it was created from, even after the source publishes a new revision.

The sample declares `content_sha256 = 1f974ece9429393b052de38052876b65ed195f83d3b6d55773691f2599f5c582`. We tried to reproduce it with three canonicalizations of `content` and `content.pages`, and none matched. The source's hashing method is unknown, so we cannot rely on it to verify integrity. This is an open question for the client.

The source already revises books: `timeline` shows 6 revisions and 7 captures, and `revision.previous_r = 5`.

## Decision

- **Our own hashes:**
  - `file_hash = sha256(file bytes)` for every input file (JSON, PDF), recorded at `integrity_register`.
  - `block_hash = "sha256:" + sha256(block.text.encode("utf-8"))`, the exact text with no normalization. Example: `b000135` → `sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989`.
  - `canonical_content_hash = sha256(canonical JSON of all blocks, sort_keys=True, separators=(",",":"), ensure_ascii=False)`.
- The source `content_sha256` is stored as `source_declared_hash`, with `verified: false` and issue `source_hash_unverified` (informational).
- **Read-only originals:** inputs are copied to `store/originals/<pub_ref>/` and made read-only (`chmod 0444`). Production uses an S3/MinIO bucket with object lock.
- **Invariant check** at `integrity_verify` (last step): the file hashes of `data/` and `store/originals/` are unchanged, and every anchor's `block_hash` matches its current block. If either check fails, the run fails.
- **Stale anchors:** when a new revision arrives, blocks are matched by `block_id` and compared by `block_hash`.
  - Hash equal → enrichment is carried over unchanged (same IDs).
  - Hash changed → the anchor is `stale`, issue `anchor_stale` is raised, and the affected units are re-extracted and re-reviewed.
  - Block removed → the anchor is `orphaned`, and its units are withdrawn from publishing.
  - New block → processed normally.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Own file + block + canonical hashes; stale detection (chosen)** | Independent of the unknown source method; fine-grained; enables incremental reprocessing | Extra hashing step (milliseconds) |
| B. Trust the source `content_sha256` | No work | Cannot be reproduced; unverifiable |
| C. Whole-file hash only | Simple | Any change invalidates everything; no incremental reruns |
| D. Git-style versioning of source files | Full history | Heavier; still needs block-level mapping |

## Consequences

- **+** We can prove "untouched" with a test, not just state it.
- **+** Revision updates cost only the changed blocks.
- **−** If the source renumbers block IDs between revisions, matching by `block_id` fails. Fallback: match by `block_hash`, then by normalized text similarity, and send the remaining cases to review.

## Compliance / how verified

- Test: hash every file in `data/` before and after a run → equal.
- Test: edit one block's text in a fixture copy (r7) → exactly the anchors on that block become `stale`; everything else keeps its IDs.
- Test: the manifest contains input and output hashes.

## Related

ADR-001, ADR-003, ADR-011.
