---
id: T-153
title: "Technical_Proposal.md (all assignment deliverables)"
epic: E15
priority: P0
depends_on: [T-152, T-132]
estimate: L
owner: agent
status: todo
wave: 14
---

# T-153 — Technical_Proposal.md (all assignment deliverables)

**Epic:** E15 Assignment deliverables · **Priority:** P0 · **Estimate:** L · **Wave:** 14

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
The main submission document. Must cover assignment §3 (9 items + method split), §4 (12 steps), §5 (8 deliverables), §6 (6 considerations). Use docs/09-coverage-matrix.md as checklist.

## Scope
- Sections: Executive summary · Scope understanding · Architectural principles · 1 System architecture · 2 Data flow · 3 Technology recommendations · 4 Arabic NLP & model strategy · 5 Knowledge extraction (genres, NER, source-location) · 6 Model training (datasets, LoRA/QLoRA) · 7 MVP (real numbers from SUMMARY.md) · 8 Roadmap (phases, challenges, infra, resources) · Technical considerations compliance table · Risks · Assumptions & open questions · Appendix: data findings.
- Embed PNG diagrams; English; ≤ 15 pages equivalent.

## Files
- `deliverables/Technical_Proposal.md`

## Implementation notes
- Numbers must come from the latest run (SUMMARY.md), not typed by hand.

## Acceptance criteria
- [ ] Every row of 09-coverage-matrix.md points to a section that exists.
- [ ] No claim contradicts DECISIONS §7.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
grep -c '^## ' deliverables/Technical_Proposal.md
```

## Out of scope
- Anything not listed in Scope.
