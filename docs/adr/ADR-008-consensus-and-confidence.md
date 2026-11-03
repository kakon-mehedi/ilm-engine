# ADR-008: Multi-model consensus and computed confidence

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§3.7 asks for model comparison, independent validation, consensus, confidence scoring and discrepancy detection. §6 asks that AI outputs support confidence assessment and human approval.

An LLM's own confidence score is poorly calibrated. Facts derived by rules from the sample are very reliable: all 300 `refs` resolve, and the entry numbers run 1–75. Some discrepancies are real signals in the data, not model noise:
- `quality.auto` reports claimed 72 pages, held 68. That is 5.6% short, above the 5% tolerance, yet `passed: true`.
- A naive entry regex reported entry #32 missing. It is actually mid-sentence in `b000294`. This is a reminder to double-check any "gap" before flagging it.

## Decision

- **Consensus:** for LLM tasks marked `verify: true`, two models from different families extract independently. Their results are compared **field by field** after normalization (ADR-012).
  - If they agree, confidence is multiplied by 1.2.
  - If they disagree, a judge model (Tier L) sees both outputs and the source. If it decides with evidence, the factor is 0.9. Otherwise the item becomes issue `model_disagreement` and goes to review.
- **Confidence formula** (from DECISIONS.md §8):
  ```
  confidence = clamp01(base × evidence × schema × agreement × penalties)
  base:      rule/structural 0.95 | llm 0.75
  evidence:  exact 1.0 | normalized 0.9 | none 0 (reject)
  schema:    valid 1.0 | valid after 1 repair 0.9 | invalid 0
  agreement: agree ×1.2 | judge 0.9 | single 1.0
  penalties: ambiguous entity ×0.8 | grammar mismatch ×0.7 | suspected OCR noise ×0.9
  ```
  Example: an LLM fact with exact evidence, a valid schema and two agreeing models scores 0.75 × 1.2 = 0.90. That auto-approves (≥ 0.80) unless the fact is sensitive.
- **Discrepancy detection** rules run independently of models:
  - page count vs the claimed count;
  - TOC entry without a matching block;
  - numbering gaps or duplicates, re-checked with a second parser before flagging;
  - metadata conflicts (card vs content);
  - title variants (الإخوة / الأُخوة).
- Thresholds live in config (`review.threshold.default = 0.80`, with per-category overrides). They will be adjusted later by calibrating against reviewed samples.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Score computed from verifiable signals + cross-family consensus (chosen)** | Explainable; can be calibrated; independent | Two model calls for verified tasks |
| B. Model's own confidence | Free | Uncalibrated, overconfident |
| C. Majority vote of 3+ models, always | Robust | 3× the cost; still needs the evidence check |
| D. Human review of everything | Safest | Does not scale to thousands of books |

## Consequences

- **+** Every score can be explained by its factors, stored in `ValidationResult.factors`.
- **+** Cost scales with risk: only `verify: true` tasks pay for two models.
- **−** The initial factor values are assumptions until calibration data exists.

## Compliance / how verified

- Unit tests for the formula, using the worked examples above.
- Test: the numbering check reports no gap on the sample (75 entries), and a fixture with a real gap reports `numbering_gap`.
- Test: `page_count_mismatch` is raised for 72 vs 68. It is then downgraded to informational once the missing pages are identified as non-content (cover, publisher page, basmala, blank).

## Related

ADR-006, ADR-007, ADR-009, ADR-016.
