---
id: T-094
title: "LLM extraction with mandatory evidence"
epic: E09
priority: P1
depends_on: [T-091, T-093, T-100]
estimate: M
owner: agent
status: done
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
- [x] Hallucinated quote is rejected and logged as `evidence_not_found`.
- [x] Accepted facts carry model id, prompt version, anchors.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_llm_extract.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `extract_unit_facts(gateway, UnitInput, config, origins, scan_pages, verifier=None) -> ExtractionOutcome{facts, issues, result, verifier, rejected}`; output schema `EntryFacts` (the `entry_facts.v1` prompt's schema). The unit step (T-071/T-072) calls it for units that need the LLM.
- Only quotes from blocks given to the model (entry, footnotes, heading) are accepted; one unmatched quote rejects the whole fact with `evidence_not_found` (details: predicate, quotes, model id). Null provider → `needs_llm`; invalid output after the repair retry → `schema_invalid`.
- Accepted facts: origin of the first evidence block (`author_text` / `editor_footnote`), `ai_generated` when inferred (ADR-010); confidence from §8 (`llm` base, normalized evidence 0.9, repaired schema 0.9, `ambiguous_quote` penalty), so a single-model fact scores 0.75 and goes to review.
- With `llm.verifier` configured, the verifier runs on the same input independently and its result is returned for consensus (T-102); agreement is applied there.
