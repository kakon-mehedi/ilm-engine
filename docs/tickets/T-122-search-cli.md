---
id: T-122
title: "Search CLI"
epic: E12
priority: P1
depends_on: [T-120, T-142]
estimate: S
owner: agent
status: done
wave: 10
---

# T-122 — Search CLI

**Epic:** E12 Search · **Priority:** P1 · **Estimate:** S · **Wave:** 10

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Show search working from the terminal.

## Scope
- `ilm-engine search "<query>" --book <pub_ref> [--semantic]` prints top-k with page, block, quote, origin.

## Files
- `src/ilm_engine/cli.py`
- `tests/test_search_cli.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] `ilm-engine search "الدارقطني"` prints results with page numbers and RTL text.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_search_cli.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `ilm-engine search "<query>" [--book <pub_ref>] [--out output] [--limit 10] [--semantic]`: one line per hit with rank, kind (unit/entity/block), printed page, block ID, origin layer (from `origin_map.json`), score and the original text (RTL Arabic as stored). `--book` may be omitted when the output root holds a single run; `--semantic` uses the hybrid ranking (falls back to lexical without the model).
