# ADR-009: Sensitive content is always human-reviewed

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

Step 10 of the expected data flow says: "Send uncertain **or sensitive** results for human review". Confidence (ADR-008) covers uncertainty. Sensitivity is about the cost of an error, not how likely it is. A wrongly published hadith grading or ruling misleads readers on religious matters even when the model was "confident".

Sensitive content appears even in this genealogy book:
- `b000228` (p. 35, footnote): "رواه الطبراني في "الكبير" (٣/ ١٦٦) … وإسناده ضعيف لكثرة المجاهيل." This is a hadith grading.
- The 8 spans with class `c1` appear to mark Prophetic speech (inferred meaning).
- Narrator identity: one name can refer to several narrators, and picking the wrong person rewires the graph.

## Decision

- `validation/sensitivity.py` tags items with these categories: `prophetic_attribution`, `hadith_grading`, `fiqh_ruling`, `aqeedah_proposition`, `narrator_disambiguation`.
- Any item with a sensitive tag gets `review_status: pending_review` and issue `sensitive_content`, **whatever its confidence**.
- Detection is rule-first, using lexicons such as "إسناده ضعيف/صحيح/حسن" and "قال رسول الله". There is also a schema-level flag: any field a genre plugin declares `sensitive=True` (ADR-013), such as fiqh `hukm`, is always routed to review.
- Published output marks AI-generated religious interpretations as `ai_generated`. They are never presented as verified scholarly statements until a reviewer with the `scholar_reviewer` role approves them.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Mandatory review by category (chosen)** | Clear, auditable policy; protects the riskiest content | More reviewer load for hadith and fiqh books |
| B. Only a higher threshold (e.g. 0.99) | Fewer reviews | Confidence is not correctness; errors still auto-publish |
| C. Exclude sensitive content from extraction | No risk | Fails §2.F, which requires hadith grading and fiqh rulings |
| D. Review everything | Safest | Does not scale |

## Consequences

- **+** Matches the domain's expectations for religious accuracy.
- **−** Reviewer capacity becomes the bottleneck for fiqh and hadith books. Priority ordering and a batch review UI (ADR-016) reduce this.
- **−** The lexicons can miss cases. The schema-level flags are a second safety net.

## Compliance / how verified

- Test: the hadith grading in `b000228` produces a review item tagged `hadith_grading`, even at confidence 0.95.
- Test: an item with confidence 0.99 and tag `fiqh_ruling` is never `auto_approved`.

## Related

ADR-008, ADR-013, ADR-016.
