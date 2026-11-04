---
id: T-105
title: "Review queue, decisions loop + static HTML reviewer view"
epic: E10
priority: P0
depends_on: [T-103, T-104, T-101]
estimate: M
owner: agent
status: done
wave: 10
---

# T-105 — Review queue, decisions loop + static HTML reviewer view

**Epic:** E10 Validation & human review · **Priority:** P0 · **Estimate:** M · **Wave:** 10

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Section 3.8 / step 10: uncertain or sensitive results go to humans with everything needed to decide.

## Scope
- `review_queue.json` items: `{id, target{kind,id}, reason_codes[], priority, confidence, breakdown, original_text (anchored excerpt), proposed_value, model_outputs[], scan_page, pdf_page_link, status:'pending_review', allowed_actions:['approve','reject','edit','reprocess']}`.
- Priority: sensitive > model_disagreement > low confidence > info.
- Reviewer decisions file `review_decisions.json` (`[{review_id, action: approve|reject|edit|reprocess, edited_value?, reviewer, note, decided_at}]`) applied with `ilm-engine review apply <decisions.json> --book <pub_ref>`: updates statuses (`approved`, `rejected`, `edited`, `reprocess_requested`), appends an audit entry (reviewer, time, before/after) and re-writes affected outputs.
- Static `review.html` (no server) listing items with Arabic RTL text and a link to the PDF page `#page=<scan_page>`.
- Every `approved`/`edited` item is appended to `output/<pub_ref>/training_examples.jsonl` (`{task, input_excerpt, anchors, output, source:'human_review', review_id}`) — future fine-tuning data (ADR on model training).

## Files
- `src/ilm_engine/validation/review_queue.py`
- `src/ilm_engine/validation/review_html.py`
- `tests/test_review_queue.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] Queue contains b000215 nested-footnote item, b000228 grading item, all inferred relations, all `needs_llm` items.
- [x] Applying a decision changes status and appends audit; re-running pipeline keeps decisions (keyed by deterministic ID).
- [x] review.html opens offline and renders RTL.
- [x] Applying a sample decisions file with 1 approve + 1 edit writes exactly 2 lines to training_examples.jsonl.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_review_queue.py -q
```

## Out of scope
- Argilla (T-165).

## Follow-ups
- Items follow the contract `ReviewItem` (the ticket's `reason_codes`/`breakdown`/`original_text` map to `reason`, the item's `confidence` + validation factors, and `anchors` quotes; allowed actions are the `ReviewDecision.decision` values). One item per target: every non-auto-approved validation result plus issues needing a person (sensitive_content, model_disagreement, ambiguous_entity, metadata_conflict, needs_llm, nested/unlinked footnotes, broken refs, unresolved internal refs, numbering, evidence/schema problems). Issue anchors come first (they explain the reason), max 10 anchors.
- Priority 0 sensitive (scholar_reviewer) → 1 discrepancy → 2 low confidence → 3 needs_llm → 4 structural; then lowest confidence. On the sample the queue has b000215 (nested footnote), the takhrij grading in b000228 (via the unit whose span holds b000227), every inferred relation and the book-level needs_llm item.
- `ilm-engine review apply <decisions.json> --book <pub_ref>`: validates IDs, refuses non-scholar decisions on sensitive items, updates `review_queue.json` statuses, merges into `review_decisions.json`, appends `review_audit.jsonl` (reviewer, role, time, old/new) and, for approved/edited items, `training_examples.jsonl`. The pipeline re-applies `review_decisions.json` on reruns (keyed by deterministic review IDs). Updating the target records' own `review_status` in the consolidated output is done by export (T-112).
- `review.html` is written by the `review_queue` step (and `ilm-engine review html`): static, RTL, offline, quotes highlighted in their block, link to the stored PDF `#page=<scan_page>`.
- `validate` now tags every footnote linked to a unit, not only the entry note.
