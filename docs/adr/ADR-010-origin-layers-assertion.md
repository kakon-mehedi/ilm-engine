# ADR-010: Origin layers and stated/inferred assertion

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§6 says: "Original author statements are distinguished from AI-generated interpretations." The sample shows that "the original" has more than one author:

| Pages / blocks | Voice |
|---|---|
| 3–16 (e.g. `b000012` "مقدمة المحقق", `b000018`) | The muhaqqiq (editor) Basim Faisal al-Jawabira |
| 17 (manuscript title page with the chain of narration) | Transmitters |
| 19 (`b000090` "مقدمة المؤلف", then "أخبرنا الشيخ الفقيه …") | Transmitters' isnad, not al-Daraqutni's words |
| 20 from `b000098` ("ذكر الأُخوة ممن صحب النبي …") to 72 | Al-Daraqutni (author) |
| End of 72 (copyist notes; footnote `b000592` "هذا من كلام ناسخ الأصل") | Copyist / transmitters |
| All 317 `footnote` blocks | The muhaqqiq |

Facts also differ in how they are known. Fatimah's marriage to Ali in year 2 AH is **stated** in footnote `b000109`, which is the editor's voice, not the author's. "Fatimah is a daughter of the Prophet ﷺ" is **inferred** from heading `b000104` "أولاد رَسول الله" plus entry `b000105`. Recording it as a plain fact would misrepresent the source.

Classifying by block `kind` alone is wrong, because the editor's introduction consists of `text` blocks.

## Decision

- Every block and every fact carries an `origin`: `author_text` | `transmission_isnad` | `editor_text` | `editor_footnote` | `ai_generated`.
- `processors/origin.py` assigns block origin **per section** using rules:
  1. any `footnote` → `editor_footnote`;
  2. blocks before the author-introduction `toc_heading` (`مقدمة المؤلف`) → `editor_text`, except a manuscript title page detected by the pattern "تأليف … رواية" → `transmission_isnad`;
  3. blocks starting with transmission formulae (`أخبرنا`, `أنا`, `حدثنا` at block start within the introduction section) → `transmission_isnad`;
  4. otherwise, within the author section → `author_text`.
  Per-book overrides in `config/books/<pub_id>.yaml` take precedence and are listed in `origin_map.json`.
- Every fact carries an `assertion`:
  - `stated`: explicit in the cited text. Its origin is the origin of the evidence block.
  - `inferred`: derived by the system. Its origin is always `ai_generated`, and it must cite all supporting anchors.
- Output records that are generated text (summaries, labels) are always `ai_generated`.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Section-based origin + stated/inferred assertion (chosen)** | Matches the real structure; explainable; overridable per book | Needs per-source rules; some books need overrides |
| B. Origin from block `kind` only (text = author, footnote = editor) | Trivial | Wrong for editor introductions and isnad |
| C. LLM classifies the voice of each block | Flexible | Non-deterministic; costly; unnecessary when the structure is clear |
| D. A single "AI vs original" flag | Simple | Loses editor vs author vs transmitter distinctions that scholars care about |

## Consequences

- **+** The UI can show "Daraqutni says", "the editor notes" or "the system infers", which satisfies §6 bullet 4.
- **+** Reviewers can filter inferred facts.
- **−** New sources may need new origin rules or overrides.

## Compliance / how verified

- Test on the sample: `b000098` → `author_text`; the "أخبرنا الشيخ" block on page 19 → `transmission_isnad`; `b000018` → `editor_text`; `b000109` → `editor_footnote`.
- Test: every fact with `assertion: inferred` has `origin: ai_generated` and at least 2 anchors (e.g. heading + entry).

## Related

ADR-003, ADR-007, ADR-009.
