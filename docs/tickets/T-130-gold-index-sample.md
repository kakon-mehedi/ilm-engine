---
id: T-130
title: "Gold sample from printed index (PDF pp. 76–80)"
epic: E13
priority: P1
depends_on: [T-001]
estimate: M
owner: agent
status: todo
wave: 1
---

# T-130 — Gold sample from printed index (PDF pp. 76–80)

**Epic:** E13 Evaluation · **Priority:** P1 · **Estimate:** M · **Wave:** 1

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
The editor's printed index of narrators with biographies (فهرس الرواة المترجم لهم) is human ground truth. PDF has no text layer; OCR is out of scope, so we transcribe a sample for evaluation only.

## Scope
- Render pages with `pdftoppm -f 76 -l 80 -r 150 -png data/demo_book_daraqutni_v1.pdf eval/pages/p` and read them (image reading by the agent) to transcribe ≥40 entries: `{name, page_in_book}`.
- Save `eval/gold_index_sample.json` with `{source:'printed_index', pdf_pages:[76..80], transcribed_by, entries:[…]}`; mark uncertain readings.

## Files
- `eval/gold_index_sample.json`
- `eval/README.md`

## Implementation notes
- Verify which pages hold فهرس الرواة first (pp. 73–80 contain all three indexes).

## Acceptance criteria
- [ ] ≥ 40 entries with page numbers; each spot-checked against the rendered image.
- [ ] README explains it is evaluation data, not pipeline input.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
python3 -c "import json;d=json.load(open('eval/gold_index_sample.json'));assert len(d['entries'])>=40"
```

## Out of scope
- Building an OCR pipeline.
