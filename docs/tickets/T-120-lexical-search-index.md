---
id: T-120
title: "Normalized lexical search index"
epic: E12
priority: P1
depends_on: [T-060, T-071]
estimate: S
owner: agent
status: done
wave: 9
---

# T-120 — Normalized lexical search index

**Epic:** E12 Search · **Priority:** P1 · **Estimate:** S · **Wave:** 9

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement D: search that tolerates diacritics and spelling variants (MVP stand-in for OpenSearch).

## Scope
- `search/lexical.py`: inverted index over normalized tokens of blocks + units + entity names; BM25 scoring; results return anchors.
- Write `search_index.json`.

## Files
- `src/ilm_engine/search/lexical.py`
- `tests/test_lexical.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] Query 'الدارقطني' and 'الدَّارقطني' return identical result lists.
- [x] Query 'هند بنت عتيق' ranks unit #8 first.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_lexical.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `search_index.json` = `{version, normalizer_version, pub_ref, documents[{doc_id, kind, title, length, anchor}], avg_length, postings{token: [[doc, tf]]}}`, sorted for byte-stable output. Documents: every block with words (583 of 594; the 11 "* * * * *" separators have no tokens), every unit (person surface + entry text), every entity (canonical name + aliases, once T-080 exists).
- Tokens are the `search`-normalized copy (ADR-012), so query variants match identically; BM25 (k1 1.2, b 0.75) with kind boosts unit 1.5 / entity 1.3 / block 1.0 and deterministic tie-breaks. Block anchors cover the whole block with the quote truncated at 120 characters (`quote_truncated`).
- `search(index, query, limit, kinds)` is the API the search CLI (T-122) uses. Roots/lemmas from the optional morphology adapter (T-063) are not indexed yet (morphology is off by default).
