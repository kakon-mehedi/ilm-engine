---
id: T-091
title: "Anthropic provider (primary extractor)"
epic: E09
priority: P1
depends_on: [T-090]
estimate: S
owner: agent
status: todo
wave: 3
---

# T-091 — Anthropic provider (primary extractor)

**Epic:** E09 LLM gateway & genre extraction · **Priority:** P1 · **Estimate:** S · **Wave:** 3

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Primary extraction model: `claude-sonnet-5-5`; hard cases/judge escalation: `claude-opus-5-5`.

## Scope
- `providers/anthropic.py` using the `anthropic` SDK, key from `ANTHROPIC_API_KEY`, temperature 0, JSON output via tool/schema.
- Model ids configurable; record exact model id in result.

## Files
- `src/ilm_engine/llm/providers/anthropic.py`
- `tests/test_anthropic_provider.py`

## Implementation notes
- Tests mock the SDK; a live test is marked `@pytest.mark.live` and skipped without key.

## Acceptance criteria
- [ ] Mocked call returns a validated object and correct model id.
- [ ] Missing key → clear error only if provider selected.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_anthropic_provider.py -q
```

## Out of scope
- Anything not listed in Scope.
