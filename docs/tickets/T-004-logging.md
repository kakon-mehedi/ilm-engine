---
id: T-004
title: "Structured logging"
epic: E00
priority: P1
depends_on: [T-001]
estimate: S
owner: agent
status: done
wave: 1
---

# T-004 — Structured logging

**Epic:** E00 Setup · **Priority:** P1 · **Estimate:** S · **Wave:** 1

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Every step logs in a machine-readable way so a run can be audited (observability, cross-cutting layer).

## Scope
- `logging_setup(level, json: bool)` in `ilm_engine/__init__.py` or `log.py`; JSON lines with `ts, level, run_id, step, pub_ref, msg, extra`.
- CLI flag `--log-json`.

## Files
- `src/ilm_engine/log.py`
- `tests/test_log.py`

## Implementation notes
- Never log full book text; log block IDs.

## Acceptance criteria
- [x] A log call emits one JSON object per line containing `run_id` and `step` when set.
- [x] Arabic text is emitted as UTF-8 (no `\u` escapes).
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_log.py -q
```

## Out of scope
- OpenTelemetry (T-169).

## Follow-ups
- `run_id`, `step` and `pub_ref` are set with the `log_context(...)` context manager (context variables), so the step runner (T-140) wraps each step once and every log call inside inherits them.
- Each JSON line also carries `logger` (the module logger name); `exc` is added for exceptions.
- CLI: `--log-json` plus `--log-level` on the root command; text logs remain the default.
