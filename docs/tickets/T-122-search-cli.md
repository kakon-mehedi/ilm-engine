---
id: T-122
title: "Search CLI"
epic: E12
priority: P1
depends_on: [T-120, T-142]
estimate: S
owner: agent
status: todo
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
- [ ] `ilm-engine search "الدارقطني"` prints results with page numbers and RTL text.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_search_cli.py -q
```

## Out of scope
- Anything not listed in Scope.
