---
id: T-034
title: "Origin layer assignment (+ per-book override)"
epic: E03
priority: P0
depends_on: [T-032, T-002]
estimate: M
owner: agent
status: todo
wave: 5
---

# T-034 — Origin layer assignment (+ per-book override)

**Epic:** E03 Document analysis, structure, origin · **Priority:** P0 · **Estimate:** M · **Wave:** 5

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Section 6: distinguish original author statements from editor/transmitter text and AI output.

## Scope
- `processors/origin.py` assigns one `origin` per block (DECISIONS §6): footnote → `editor_footnote`; others by section rules + override ranges.
- Rules: blocks before 'مقدمة المؤلف' → `editor_text` except override `transmission_isnad` pages (17); page 19 isnad ('أخبرنا' chain) → `transmission_isnad`; from b000098 → `author_text`; tail of p.72 copyist/sama' blocks via override → `transmission_isnad`.
- Write `origin_map.json` {block_id: origin} + summary counts.

## Files
- `src/ilm_engine/processors/origin.py`
- `config/books/pub_01M0CJECV4ZHFTP02BJQ6D3STJ.yaml`
- `tests/test_origin.py`

## Implementation notes
- `ai_generated` is never assigned to source blocks.

## Acceptance criteria
- [ ] All 317 footnotes → `editor_footnote`.
- [ ] b000098 → `author_text`; b000093 (p.19 isnad) → `transmission_isnad`; b000018 (p.5) → `editor_text`; b000135 → `author_text`.
- [ ] Every block has exactly one origin.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_origin.py -q
```

## Out of scope
- Anything not listed in Scope.
