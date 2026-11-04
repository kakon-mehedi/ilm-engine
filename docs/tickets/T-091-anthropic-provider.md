---
id: T-091
title: "Anthropic provider (primary extractor)"
epic: E09
priority: P1
depends_on: [T-090]
estimate: S
owner: agent
status: done
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
- [x] Mocked call returns a validated object and correct model id.
- [x] Missing key → clear error only if provider selected.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_anthropic_provider.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- **Temperature is not sent.** Current Claude models (Sonnet 5.5, Opus 5.5) reject sampling parameters and forced `tool_choice` with a 400, so "temperature 0 + JSON via tool" is implemented as structured outputs (`output_config.format` with the task's JSON Schema, made strict with `additionalProperties: false`). Repeatability comes from the gateway's response cache (ADR-006/011 still hold for reruns). ADR-006's "temperature 0" should be read as "deterministic reruns via cache".
- Default model `claude-sonnet-5-5` (ADR-006 primary extractor); the gateway's `model` overrides it per route, and the answering model id from the response is recorded.
- Server-side refusal fallback is enabled by default (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`); `fallbacks=False` uses the plain Messages API. A refusal yields an invalid output (→ repair → `schema_valid=False`), never an exception.
- The SDK is imported lazily: a missing package or missing credentials raise `ProviderConfigError` only when the provider is actually used. Credentials are resolved by the SDK (env key, auth token or `ant auth login` profile).
- The live test is marked `live` (marker registered in pyproject) and skipped without `ANTHROPIC_API_KEY`.
