# ADR-016: Human review — JSON + HTML for MVP, Argilla for production

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§3.8 asks for mechanisms for reviewing and approving AI-generated outputs. Step 10 sends uncertain or sensitive results to human review, and step 11 stores only approved information.

Review items expected from the sample:
- the hadith grading in `b000228` (sensitive, ADR-009);
- the nested footnote `b000215` (marker "أ", page 33), which has no `refs` because the JSON never links footnote to footnote;
- the `page_count_mismatch` (72 vs 68);
- LLM-only tasks (`needs_llm`) when running without an API key.

Reviewers need to see:
- the original text, with the anchor highlighted;
- the PDF page (`scan_page`);
- the extracted item;
- each model's output;
- confidence factors;
- validation errors.

Their actions are approve, reject, edit and request reprocessing.

## Decision

- **MVP:** `review_queue.json`, a list of `ReviewItem` (see the data contracts), sorted by priority:
  - sensitive first;
  - then lowest confidence;
  - then by the number of downstream facts that depend on the item.

  `ilm-engine review html` renders a static, read-only `review.html` (RTL Arabic, highlighted quote, link to the PDF page). Decisions are recorded with `ilm-engine review apply decisions.json`, which updates status and writes an audit entry.
- **Production:** Argilla, self-hosted. It supports annotation projects, multiple reviewers, role-based access and exports for training. Review projects are created per genre and per sensitivity category.
- **Roles:**
  - `editor_reviewer`: metadata, structure, annotations.
  - `scholar_reviewer`: required for any sensitive category.
  - `admin`.
- **Audit:** every decision stores reviewer id, role, timestamp, previous value, new value and reason. Decisions survive reruns because IDs are deterministic (ADR-011).
- **Feedback:** approved and edited items are exported as training candidates (ADR-015).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. JSON + static HTML (MVP), Argilla (production) (chosen)** | Zero infrastructure now; mature open-source tool later; training exports | Two UIs over time |
| B. Label Studio | Very flexible labeling UI | Less focused on LLM-output review and feedback loops; more setup |
| C. Custom React review app from day one | Exact fit | Weeks of work; not needed to prove the design |
| D. Spreadsheet review | Familiar | No anchors, no audit, error-prone |

## Consequences

- **+** Reviewers see the exact evidence, which speeds decisions.
- **−** The static HTML in the MVP cannot record decisions by itself. The CLI apply step covers this.

## Compliance / how verified

- Test: `review_queue.json` contains items for `b000228` (hadith_grading) and `b000215` (nested_footnote), ordered with sensitive items first.
- Test: applying an `edited` decision changes the fact, keeps the old value in the audit trail, and leaves the ID unchanged.

## Related

ADR-008, ADR-009, ADR-011, ADR-015.
