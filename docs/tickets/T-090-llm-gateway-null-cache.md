---
id: T-090
title: "LLM gateway, null provider, response cache"
epic: E09
priority: P0
depends_on: [T-002]
estimate: M
owner: agent
status: done
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
- [x] With provider null, full pipeline completes and LLM-dependent items carry `needs_llm`.
- [x] Provider `fixture` replays a recorded response deterministically and raises on a missing fixture.
- [x] Second identical call returns `cached=True` without provider call (mock).
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_gateway.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- One result type reconciles the ticket, ADR-006 and 02-architecture §7: `LLMResult{output, model, provider, task, prompt_version, raw, cached, repaired, schema_valid, needs_llm, errors, usage}`. `task` is the prompt id.
- Providers implement `complete(LLMRequest) -> ProviderResponse | None` (`llm/providers/base.py`) and only produce raw text; the gateway handles caching, JSON extraction (bare or fenced), Pydantic validation and the single repair retry.
- The cache key is sha256 over provider + model + task + prompt version + canonical input; entries are written atomically, corrupt entries count as misses, and null results are never cached. A repaired answer is cached together with its repair, so replays make no calls.
- `providers/fixture.py` names fixtures by the provider-independent `request_key` (`tests/fixtures/llm/<key>.json`, `<key>.repair.json` for repair turns); `record_fixture` writes them.
- The gateway cannot know the affected record, so null results carry `needs_llm=True` and callers build the issue with `needs_llm_issue(...)`. "Full pipeline completes with provider null" is re-checked end to end in T-143.
- `get_provider(name)` imports `ilm_engine.llm.providers.<name>` on demand, so T-091/T-092 providers register themselves.
