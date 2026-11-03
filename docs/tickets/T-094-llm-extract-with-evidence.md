---
id: T-094
title: "LLM extraction with mandatory evidence"
epic: E09
priority: P1
depends_on: [T-091, T-093, T-100]
estimate: M
owner: agent
status: todo
wave: 4
---

# T-094 — LLM extraction with mandatory evidence

**Epic:** E09 LLM gateway & genre extraction · **Priority:** P1 · **Estimate:** M · **Wave:** 4

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
LLM handles what rules cannot (group bounds, elliptic names, complex facts); every claim must quote the source.

## Scope
- `extractors/llm_extract.py`: for units flagged `needs_llm`, call extractor with unit text + footnotes; output facts with `quote`.
- Pass every fact through the evidence guard (T-100); drop unmatched with `evidence_not_found`.
- If `llm.verifier` configured, run it independently and send both to consensus (T-102).

## Files
- `src/ilm_engine/extractors/llm_extract.py`
- `tests/test_llm_extract.py`

## Implementation notes
- Tests use a fake provider returning fixed JSON including one hallucinated quote.

## Acceptance criteria
- [ ] Hallucinated quote is rejected and logged as `evidence_not_found`.
- [ ] Accepted facts carry model id, prompt version, anchors.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_llm_extract.py -q
```

## Out of scope
- Anything not listed in Scope.
