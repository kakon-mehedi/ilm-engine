# ADR-007: Evidence-grounded extraction (hallucination guard)

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

In religious literature, an invented narrator, date or ruling is a serious error. §6 requires traceability and requires that author statements be kept apart from AI interpretation. §3.7 asks for independent validation and discrepancy detection.

An LLM can produce a plausible fact that is not in the text. For example, it might give a death year for Hind bint Atiq, but `b000135` states none. The text only says "أسلمت (٢) وتزوجت، ولم يُروَ عنها شيءٌ (٣)".

## Decision

1. Every LLM extraction schema requires an `evidence` list of `{block_id, quote}` for each fact. The quote must be copied verbatim from the input.
2. `validation/evidence.py` looks for each quote in the original block text:
   - **Exact match:** offsets are computed, and the evidence factor is 1.0.
   - **Match only after search normalization (ADR-012):** offsets are mapped back to the original text, and the factor is 0.9.
   - **No match:** the fact is **rejected** (factor 0) with issue `evidence_not_found`. It is never stored as a fact.
3. If the quote occurs more than once in the block, the occurrence closest to the model's optional `hint_start` is used. With no hint, the first occurrence is used, with a ×0.9 penalty.
4. A fact that is derived rather than stated must set `assertion: "inferred"` and cite the heading and entry blocks as evidence (ADR-010). Example: `child_of` the Prophet ﷺ, derived from heading `b000104` "أولاد رَسول الله".
5. The LLM only sees the blocks it may cite: the entry, its footnotes and its section heading. This keeps it from wandering.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Mandatory verbatim quotes, verified by code (chosen)** | Deterministic check; offsets come for free; fabrications are rejected | A paraphrased-but-true fact still needs a quote; outputs get slightly longer |
| B. Ask the model to check itself | Cheap | Self-verification is weak and correlated |
| C. A second model judges truthfulness only | Independent | Still non-deterministic; no offsets |
| D. Trust high-confidence outputs | Fast | Model confidence is not calibrated |

## Consequences

- **+** No stored fact lacks an anchor, which satisfies §6 bullet 3 by construction.
- **+** Rejections are measurable: the `evidence_not_found` rate per prompt version.
- **−** A fact spread across sentences needs several quotes.
- **−** Offsets from normalized matching must be mapped back carefully (tested).

## Compliance / how verified

- Unit test: a fake model output claiming "توفيت سنة ٢٠" for `b000135` is rejected with `evidence_not_found`.
- Unit test: the quote "ولم يروَ عنها شيء" (missing some diacritics) matches through normalization and maps back to 78–97 on `b000135`.
- Property test: every stored fact has at least one anchor that passes the ADR-003 invariants.

## Related

ADR-003, ADR-006, ADR-008, ADR-010, ADR-012.
