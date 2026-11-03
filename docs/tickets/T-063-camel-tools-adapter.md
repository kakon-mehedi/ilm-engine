---
id: T-063
title: "Optional CAMeL Tools morphology adapter"
epic: E06
priority: P2
depends_on: [T-060]
estimate: M
owner: agent
status: todo
wave: 2
---

# T-063 — Optional CAMeL Tools morphology adapter

**Epic:** E06 Arabic NLP · **Priority:** P2 · **Estimate:** M · **Wave:** 2

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement D: morphological analysis, root, lemma. Optional so the MVP runs without heavy deps.

## Scope
- `nlp/morphology.py` interface `analyze(word) -> [{lemma, root, pos}]`; implementation uses CAMeL Tools if `features.camel_tools` and installed, else a stub returning [] and logging once.
- Add `roots`/`lemmas` to search index entries when available.

## Files
- `src/ilm_engine/nlp/morphology.py`
- `tests/test_morphology.py`

## Implementation notes
- Tests for the real backend are skipped if camel-tools not installed.

## Acceptance criteria
- [ ] Without camel-tools the pipeline runs and `analyze` returns [].
- [ ] With camel-tools, 'أسلمت' yields root containing س-ل-م.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_morphology.py -q
```

## Out of scope
- Farasa (production option).
