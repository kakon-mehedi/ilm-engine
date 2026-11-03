---
id: T-022
title: "Integrity invariant tests"
epic: E02
priority: P0
depends_on: [T-021, T-143]
estimate: S
owner: agent
status: todo
wave: 13
---

# T-022 — Integrity invariant tests

**Epic:** E02 Integrity · **Priority:** P0 · **Estimate:** S · **Wave:** 13

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Automated proof that a full run never changes original content and that every anchor is valid.

## Scope
- Test 1: sha256 of every file in `data/` before and after `ilm-engine run` is identical.
- Test 2: every anchor in every output satisfies `block.text[start:end] == quote` and `block_hash` matches.
- `ilm-engine verify <output_dir>` runs the same checks (exit 1 on failure).

## Files
- `tests/test_invariants.py`
- `src/ilm_engine/integrity/verify.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Both tests pass on the sample.
- [ ] Corrupting one anchor offset in a copied output makes `verify` exit 1 and name the anchor.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_invariants.py -q
uv run ilm-engine verify output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6
```

## Out of scope
- Anything not listed in Scope.
