---
id: T-104
title: "Sensitivity rules (always human review)"
epic: E10
priority: P0
depends_on: [T-095]
estimate: S
owner: agent
status: done
wave: 6
---

# T-104 — Sensitivity rules (always human review)

**Epic:** E10 Validation & human review · **Priority:** P0 · **Estimate:** S · **Wave:** 6

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Religiously sensitive outputs always go to a human, whatever their confidence.

## Scope
- `validation/sensitivity.py` tags items with categories: `prophetic_attribution` (c1 spans / quoted Prophetic speech, 'قال رسول الله'), `hadith_grading` (صحيح/حسن/ضعيف/موضوع near إسناد), `fiqh_ruling`, `aqeedah_proposition`, `narrator_disambiguation`.
- Tagged → issue `sensitive_content` + status `pending_review`.

## Files
- `src/ilm_engine/validation/sensitivity.py`
- `tests/test_sensitivity.py`

## Implementation notes
- Follow DECISIONS.md; no extra notes.

## Acceptance criteria
- [x] b000228 grading 'وإسناده ضعيف' → hadith_grading → pending_review even with confidence 0.95.
- [x] The 8 c1 spans produce prophetic_attribution tags.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_sensitivity.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- `tag_block(block, pub_ref, scan_page, genres)` → `SensitiveTag{category, rule, anchor}`; `payload_categories(payload, plugin.sensitive_fields)` for genre schemas; `enforce(status, categories)` never lets a sensitive item stay auto-approved; `sensitive_issue(...)` builds `sensitive_content`.
- Lexicons: hadith grading next to an isnad term, Prophetic-speech formulas; fiqh and aqeedah lexicons apply only when the book (or section) is of that genre, so a biography's narrative is not flagged as fiqh. Span class c1 → prophetic_attribution (8 spans on the sample, e.g. b000131 31–66).
- `narrator_disambiguation` has no lexicon: entity linking (T-081) tags it when one name may be several narrators.
- The span-class meanings (DECISIONS §12c) are a constant here; they become config if a source uses other classes.
