---
id: T-090
title: "LLM gateway, null provider, response cache"
epic: E09
priority: P0
depends_on: [T-002]
estimate: M
owner: agent
status: todo
wave: 2
---

# T-090 — LLM gateway, null provider, response cache

**Epic:** E09 LLM gateway & genre extraction · **Priority:** P0 · **Estimate:** M · **Wave:** 2

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
All model calls go through one gateway so models can be swapped and runs repeated (temperature 0 + cache).

## Scope
- `llm/gateway.py`: `complete_json(task, prompt_version, input, schema) -> LLMResult{model, prompt_version, output, raw, usage, cached}`.
- `providers/null.py`: returns `None` result + issue `needs_llm` (default; MVP runs with no API key).
- `providers/fixture.py`: replays recorded responses from `tests/fixtures/llm/<cache-key>.json`; missing fixture → test failure (never network). Used by CI and the test plan.
- `llm/cache.py`: key = sha256(provider+model+prompt_version+canonical_json(input)); stored in `.cache/llm/`.
- Schema validation with one repair retry (schema factor 0.9).

## Files
- `src/ilm_engine/llm/gateway.py`
- `src/ilm_engine/llm/providers/null.py`
- `src/ilm_engine/llm/cache.py`
- `tests/test_gateway.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] With provider null, full pipeline completes and LLM-dependent items carry `needs_llm`.
- [ ] Provider `fixture` replays a recorded response deterministically and raises on a missing fixture.
- [ ] Second identical call returns `cached=True` without provider call (mock).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_gateway.py -q
```

## Out of scope
- Anything not listed in Scope.
