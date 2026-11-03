---
id: T-003
title: "Deterministic ID generation (ids.py)"
epic: E00
priority: P0
depends_on: [T-001]
estimate: S
owner: agent
status: todo
wave: 1
---

# T-003 — Deterministic ID generation (ids.py)

**Epic:** E00 Setup · **Priority:** P0 · **Estimate:** S · **Wave:** 1

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Same input must always produce the same IDs so runs are repeatable and diffable (Section 6: repeatable).

## Scope
- `make_id(prefix: str, pub_ref: str, natural_key: str) -> str` returning `<prefix>_<sha256(pub_ref + '|' + natural_key)[:12]>`.
- Allowed prefixes exactly: `sec, ku, ent, rel, ann, cit, wrk, iss, rev, run` (DECISIONS §4); anything else raises.
- `pub_ref(pub_id, revision) -> 'pub_…@r6'`.

## Files
- `src/ilm_engine/ids.py`
- `tests/test_ids.py`

## Implementation notes
- `run` IDs may include the start timestamp; every other ID must not.

## Acceptance criteria
- [ ] `pub_ref('pub_01M0CJECV4ZHFTP02BJQ6D3STJ', 6) == 'pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6'`.
- [ ] Same inputs → identical ID; different natural key → different ID.
- [ ] Invalid prefix raises `ValueError`.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_ids.py -q
```

## Out of scope
- Anything not listed in Scope.
