---
id: T-014
title: "Adapter golden-file contract tests"
epic: E01
priority: P0
depends_on: [T-012]
estimate: S
owner: agent
status: todo
wave: 4
---

# T-014 — Adapter golden-file contract tests

**Epic:** E01 Canonical model + adapters · **Priority:** P0 · **Estimate:** S · **Wave:** 4

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Contract tests prove an adapter keeps producing the same canonical output; they run first when a new JSON format appears.

## Scope
- `tests/golden/shamela_v3/input_excerpt.json` (pages 21 and 25 + metadata) and `expected_canonical.json`.
- Test: adapter(input) == expected (byte-identical canonical JSON).
- `make golden-update` / `uv run python -m ilm_engine.tools.update_golden` to regenerate intentionally.

## Files
- `tests/golden/shamela_v3/*`
- `tests/test_golden_adapters.py`
- `src/ilm_engine/tools/update_golden.py`

## Implementation notes
- Excerpt must include b000104–b000112 and b000134–b000146.

## Acceptance criteria

- [ ] Golden files are regenerated only via `ilm-engine dev regen-goldens` (explicit human request); normal test runs never rewrite them.
- [ ] Golden test passes; changing adapter mapping makes it fail with a readable diff.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_golden_adapters.py -q
```

## Out of scope
- Anything not listed in Scope.
