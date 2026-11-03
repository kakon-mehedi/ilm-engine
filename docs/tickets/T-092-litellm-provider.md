---
id: T-092
title: "LiteLLM provider (second, independent model family)"
epic: E09
priority: P1
depends_on: [T-090]
estimate: S
owner: agent
status: todo
wave: 3
---

# T-092 — LiteLLM provider (second, independent model family)

**Epic:** E09 LLM gateway & genre extraction · **Priority:** P1 · **Estimate:** S · **Wave:** 3

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Independent verification requires a model from a different family (GPT, Gemini, or open-weight Qwen/Jais via an OpenAI-compatible endpoint).

## Scope
- `providers/litellm.py` with configurable `model` string and `api_base`.
- Gateway config `llm.verifier` separate from `llm.extractor`; refuse same family for both (config validation).

## Files
- `src/ilm_engine/llm/providers/litellm.py`
- `tests/test_litellm_provider.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Config with extractor and verifier from the same family fails validation.
- [ ] Mocked call works.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_litellm_provider.py -q
```

## Out of scope
- Anything not listed in Scope.
