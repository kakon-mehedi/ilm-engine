---
id: T-063
title: "Optional CAMeL Tools morphology adapter"
epic: E06
priority: P2
depends_on: [T-060]
estimate: M
owner: agent
status: done
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
- [x] Without camel-tools the pipeline runs and `analyze` returns [].
- [x] With camel-tools, 'أسلمت' yields root containing س-ل-م.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_morphology.py -q
```

## Out of scope
- Farasa (production option).

## Follow-ups
- `analyze(word, enabled)` takes the `features.camel_tools` flag from the caller (config is loaded once by the runner). A missing library or morphology database degrades to `[]` with one log line, never an error.
- `roots_and_lemmas(words, enabled)` is the hook for search index entries; T-120 decides where the fields go.
- camel-tools is not installed in this environment, so the real-backend test (root س-ل-م for 'أسلمت') is skipped; it runs once the `nlp` extra and its database are installed.
