---
id: T-093
title: "Versioned prompt files"
epic: E09
priority: P1
depends_on: [T-090]
estimate: S
owner: agent
status: todo
wave: 3
---

# T-093 — Versioned prompt files

**Epic:** E09 LLM gateway & genre extraction · **Priority:** P1 · **Estimate:** S · **Wave:** 3

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Repeatability: every output records the prompt version that produced it.

## Scope
- `llm/prompts/<task>.v<N>.md` with front matter (task, version, schema name).
- Prompts: `entry_facts.v1`, `group_bounds.v1`, `entity_disambiguation.v1`, `genre_classify.v1`, `judge.v1`, `metadata_verify.v1`.
- All prompts require verbatim `quote` for every fact and say 'return null if not in text'.

## Files
- `src/ilm_engine/llm/prompts/*.md`
- `src/ilm_engine/llm/prompts/__init__.py`
- `tests/test_prompts.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [ ] Loader returns (text, version); changing file content without bumping version fails a test (hash pinned in `prompts.lock`).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_prompts.py -q
```

## Out of scope
- Anything not listed in Scope.
