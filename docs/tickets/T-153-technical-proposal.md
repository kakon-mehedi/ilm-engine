---
id: T-153
title: "Technical_Proposal.md (all assignment deliverables)"
epic: E15
priority: P0
depends_on: [T-152, T-132]
estimate: L
owner: agent
status: done
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
- [x] Every row of 09-coverage-matrix.md points to a section that exists.
- [x] No claim contradicts DECISIONS §7.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
grep -c '^## ' deliverables/Technical_Proposal.md
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `deliverables/Technical_Proposal.md` (≈4,500 words, 15 sections): executive summary, scope, principles, architecture, data flow (12 steps → 21 pipeline steps), technology, Arabic NLP and model strategy, knowledge extraction, model training, MVP results, roadmap, compliance table, risks, assumptions/open questions, data-findings appendix. Embeds the PNG diagrams from T-152.
- All MVP figures come from run `run_1bd3442413cc` (`SUMMARY.md`, `run_manifest.json`, `eval_report.json`); the section on known limitations states what was not run live (LLM extraction) and what is not built yet.
- Data-verified corrections applied to the specs so the proposal does not contradict DECISIONS §7: "الإصابة" is quoted 145 times (not 144) in DECISIONS, PRD, test plan, ADR-018 and docs/README; the narrator index is on PDF pp. 76–79 (not 76–80) in DECISIONS, the AI strategy and the test plan. Ticket texts keep their original wording with the correction in their follow-ups.
