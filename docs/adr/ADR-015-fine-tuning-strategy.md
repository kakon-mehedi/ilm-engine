# ADR-015: Fine-tuning strategy — prompting → data → QLoRA, multi-LoRA serving

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§3.9 and Deliverable 6 ask for "fine-tuning approaches, training data preparation and infrastructure requirements for domain-specific open-weight models, including potential techniques such as LoRA/PEFT".

Reasons to fine-tune:
- lower cost per book at the scale of thousands of books;
- keeping text in-house for privacy;
- better accuracy on classical Arabic conventions such as nasab chains, takhrij formulae and grading terms.

Reasons not to fine-tune on day one:
- there is no labelled data yet;
- prompts and schemas are still changing;
- commercial models are already strong enough to produce draft labels.

Free supervision signals exist in the data:
- **Shamela structure:** 300 refs, TOC and headings give labels for structure and annotation.
- **Footnote formulae:** "رواه … (رقم: …)", "إسناده ضعيف", and locators like "الإصابة (٨/ ١٥٧)" give takhrij, grading and citation labels.
- **Printed indexes:** PDF pages 73–80 hold فهرس الأحاديث, فهرس الرواة المترجم لهم and الفهرس الإجمالي. They give gold entity lists for evaluation. They are never used for training, because they are the test set.

## Decision

Three phases with explicit gates:

1. **Prompting (Phase 0–1).** Commercial models with genre prompts, few-shot examples from the sample and strict evidence grounding (ADR-007). Every reviewed item is logged as a training candidate.
2. **Data (Phase 1–2).** Build datasets per task and per genre plugin:
   - weak labels from structure;
   - LLM drafts verified by humans (distillation);
   - reviewer edits from the review tool (active learning, uncertain items first);
   - **book-level** train/validation/test splits, so no book appears in two splits;
   - a gold test set from printed indexes and expert annotation.
   - Annotation guidelines are versioned.
3. **Fine-tune (Phase 3).** QLoRA (4-bit base) with PEFT/TRL on open-weight bases in the 7–32B range (Qwen-family instruct, Jais/ALLaM for Arabic). LoRA rank r = 16–64. Encoders (CAMeLBERT/AraBERT) are fully fine-tuned for NER and classification.
   - Serving: vLLM with **multi-LoRA**, meaning one base model plus one adapter per genre or task, selected per request through the gateway (ADR-006).
   - Infrastructure: 1–2 × A100/H100 80GB for QLoRA training; inference GPUs sized by throughput.
- **Gate to move to the fine-tuned model:** on the book-level test set, it must be within 2 F1 points of the commercial baseline and have an `evidence_not_found` rate at or below the baseline, at lower cost per book. Otherwise, keep the commercial routing.
- The goal is better extraction behaviour, **not** memorizing book content. Training data is extraction pairs, not raw book text for knowledge injection.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Prompt → data → QLoRA with gates (chosen)** | No premature training; data-driven; cheap adapters; per-genre specialisation | Requires review logging from day one |
| B. Full fine-tune of a large model | Maximum adaptation | Expensive GPUs; slow iteration; overkill |
| C. Prompting only, forever | No ML ops | High API cost at scale; data leaves premises |
| D. RAG over book text instead of fine-tuning | Good for Q&A | Does not improve structured extraction behaviour |
| E. Continued pre-training on the Islamic corpus | Better language model | Large cost; benefit uncertain; separate decision later |

## Consequences

- **+** The fine-tuning budget is spent only once the data proves its value.
- **+** Multi-LoRA keeps serving costs flat as genres are added.
- **−** Review tooling must export training-ready records (ADR-016).

## Compliance / how verified

- Roadmap phase gates in `08-roadmap.md`.
- Test (MVP): review items export to `training_examples.jsonl` with input, output, evidence and reviewer decision.

## Related

ADR-006, ADR-013, ADR-016.
