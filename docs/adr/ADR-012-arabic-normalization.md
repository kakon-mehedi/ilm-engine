# ADR-012: Arabic normalization is derived, never overwrites

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§2.D requires Arabic normalization, diacritic handling, and handling of spelling variants in classical Arabic. Examples from the sample:
- The same name with and without diacritics: "الدَّارقطني" (`b000018`) vs "الدارقطني".
- Title variants: card "الإخوة والأخوات" vs title page "الأُخوة والأَخوات" (`b000001`).
- Honorific variants: "رسول اللَّه -صلى الله عليه وسلم-" vs "رسول الله ﷺ".
- Typographic noise in a footnote: "عتيقُ ين عابد" (`b000139`, "ين" for "بن").
- Orthographic variant: "فى" for "في" (heading `b000026` "عملي فى الكتاب").

Normalizing the stored text would violate §6 ("original book content remains untouched") and break offsets (ADR-003).

## Decision

- `nlp/normalize.py` produces a **derived** `norm_text` used only for matching, search and comparison. The original text is never modified.
- Search normalization rules, in order:
  1. Unicode NFC;
  2. remove harakat and tanwin (U+064B–U+0652), the superscript alef (U+0670) and Quranic marks;
  3. remove tatweel (U+0640);
  4. map أ/إ/آ/ٱ → ا;
  5. ى → ي, ة → ه;
  6. ؤ → و, ئ → ي;
  7. Arabic-Indic digits ٠–٩ → 0–9 (in the normalized copy only);
  8. "اللَّه" → "الله" (the shadda falls under rule 2);
  9. collapse whitespace;
  10. canonicalize honorifics: "صلى الله عليه وسلم", "ﷺ" and "صلى الله عليه وآله وسلم" → token `<SAW>`.
- `normalize()` returns an **offset map** (normalized index → original index), so a match on `norm_text` can be mapped back to original offsets (used by ADR-007).
- Morphology (lemma and root) uses CAMeL Tools when installed (optional extra). The MVP's matching only needs the normalizer.
- The rules are versioned (`normalizer_version`) and recorded in the manifest.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Derived normalized copy + offset map (chosen)** | Original untouched; offsets recoverable; deterministic | The map must be built carefully |
| B. Normalize the stored text | Simple search | Destroys the original; breaks anchors |
| C. Search engine analyzer only (OpenSearch Arabic) | No custom code | Not available offline in the MVP; does not help evidence matching |
| D. LLM-based fuzzy matching | Handles odd variants | Non-deterministic; slow |

## Consequences

- **+** Matching is robust to diacritics, alif forms and honorific variants.
- **−** Aggressive rules (ة→ه) can merge distinct words. They are acceptable for search, and evidence matching tries an exact match first.

## Compliance / how verified

- Test: `normalize("الدَّارقطني") == normalize("الدارقطني")`.
- Test: `normalize("الأُخوة والأَخوات") == normalize("الاخوه والاخوات")`.
- Test: the offset map round-trips for every block in the sample.
- Test: original `data/` files are unchanged after normalization (ADR-017 invariant).

## Related

ADR-003, ADR-007.
