# 06 — AI, Arabic NLP & Model Strategy

This document covers assignment §3 items 3 (Automation), 4 (AI models), 5 (Arabic NLP), 7 (Multi-model orchestration), 8 (Human review — policy part) and 9 (Model adaptation). It also answers the request to distinguish programming / NLP / LLM / agentic work, and §5 deliverables 4 (Arabic NLP & model strategy), 5 (Knowledge extraction approach) and 6 (Model training approach).

All names, thresholds and codes follow `DECISIONS.md`.

---

## 1. Principle: cheapest reliable method first

```
deterministic rule  →  Arabic NLP  →  small/cheap model  →  large model  →  agent (multi-step)  →  human
      (exact)            (linguistic)       (bulk)            (hard cases)        (decisions)          (risk)
```

A task moves to the right only when the method on its left cannot do it reliably. Three reasons:
- Rules are exact, free, and reproducible, and they can be tested.
- LLM output must be verified (evidence guard, consensus). That verification costs time and money.
- Agents add autonomy. They are used only where the next step depends on what was found.

## 2. Task → approach matrix

| # | Task (pipeline step) | Approach | Why this | Why not the alternative |
|---|---|---|---|---|
| 1 | Receive input, select adapter, validate schema | **Programming** | Contract checking is exact | An LLM "guessing" the format would hide breaking changes |
| 2 | Integrity hashing, immutable store | **Programming** | Cryptographic, exact | — |
| 3 | Document analysis (page gaps, stats, quality) | **Programming** | Counting and comparing | — |
| 4 | Structure tree from heading/TOC | **Programming** (+ LLM fallback for sources without heading markup) | Headings are already marked in this JSON | LLM is unnecessary when markup exists |
| 5 | Origin layer assignment | **Programming** (rules + per-book YAML) + **Human** confirmation per book | Few, large ranges. One human check covers the whole book. | LLM per block is costly and could mislabel author/editor text |
| 6 | Metadata from card | **Programming** | Labelled fields (`card[].group`) | — |
| 7 | Metadata from preface (death year, manuscript info) | **LLM** with evidence | Free prose | Regex misses paraphrases ("سنةٍ خمسٍ وثمانين وثلاث مئة") |
| 8 | Metadata conflict detection | **Programming** | Compare values | — |
| 9 | Genre classification | **Programming** (source category) → **LLM** (content sample) → agent router | `category.name = الأنساب` is a strong prior. LLM confirms on content. | A trained classifier needs labelled books we do not have yet (Phase 3) |
| 10 | Related works / book family | **Agentic** (Related-Works Resolver with catalog search tool) | Needs search → compare → decide loop | One-shot LLM cannot query the catalog |
| 11 | Structural index | **Programming** | Tree + block ranges | — |
| 12 | Semantic index | **NLP / embeddings** (BGE-M3) | Meaning-level retrieval | LLM per query is too slow and costly |
| 13 | Annotation mapping (refs, continued, nested) | **Programming** | `refs` + markers | — |
| 14 | Citation extraction (external works + locators) | **Programming** (regex + alias table) → **LLM** for ambiguous titles | Titles are quoted with locators | — |
| 15 | Internal references ("ترجمة رقم (٣٣)") | **Programming** | Fixed patterns | — |
| 16 | Arabic normalization, tokenization | **NLP** (own normalizer, CAMeL Tools) | Known rules | — |
| 17 | Morphology, root, lemma | **NLP** (CAMeL Tools / Farasa) | Mature analyzers | LLMs are inconsistent at roots |
| 18 | Knowledge-unit segmentation (biographical entries) | **Programming** (entry regex on `author_text`) | Explicit numbering | — |
| 19 | Genre-specific fact extraction | **LLM** (structured output + evidence) inside **Genre Extractor agent** | Requires reading comprehension | Rules cannot capture rulings, gradings, opinions |
| 20 | Entity candidate detection (persons) | **NLP** (nasab parser + NER model) | Nasab chains follow a grammar | — |
| 21 | Entity linking / disambiguation | **NLP + LLM + Human** | Context needed. Sensitive for narrators. | Auto-pick risks wrong attributions |
| 22 | Relation extraction (sibling groups etc.) | **Programming** for closing phrases + **LLM** for free prose | "ابنا أبي هالة" is patterned. "روى عنه ابنا أختِه" is not. | — |
| 23 | Evidence guard (quote must exist) | **Programming** | String match | Never ask an LLM whether an LLM is right about a quote |
| 24 | Multi-model consensus | **Programming** (compare) + **LLM judge** | Compare is exact. The judge resolves the rest. | — |
| 25 | Discrepancy resolution | **Agentic** (Discrepancy Resolver: re-read source, ask 2nd model) | Multi-step decision | — |
| 26 | Confidence scoring | **Programming** (DECISIONS §8 formula) | External verifiable signals | LLM self-reported confidence is uncalibrated |
| 27 | Sensitivity tagging | **Programming** (category rules) + **LLM** tagger | — | — |
| 28 | Review routing & priority | **Programming** | Deterministic policy | — |
| 29 | Approval of sensitive / uncertain items | **Human** | Religious responsibility | — |
| 30 | Storage, publishing, search index build | **Programming** | — | — |
| 31 | Evaluation vs gold | **Programming** | Metrics | — |

**Agents (only four, DECISIONS §12):** Genre Router, Genre Extractor (one per genre schema), Related-Works / Citation Resolver, Discrepancy Resolver. In the MVP they are plain functions behind the same interface. In production they are LangGraph graphs.

## 3. Model matrix

| Role | Commercial (API) | Open-weight (self-hosted) | Used for |
|---|---|---|---|
| Hard reasoning / long classical prose | **Claude Opus 5.5** (`claude-opus-5-5`) | Qwen instruct family (large) | Fiqh rulings, khilaf, aqeedah propositions, escalations |
| Default extractor | **Claude Sonnet 5.5** (`claude-sonnet-5-5`) | Qwen instruct (mid size), Llama instruct | Genre extraction, metadata from prose, relations in prose |
| Bulk / cheap | **Claude Haiku 5.5** (`claude-haiku-5-5`) | Small Qwen, fine-tuned (Phase 3) | Genre tagging, sensitivity tagging, simple classification |
| Independent verifier / judge | **GPT** or **Gemini** (a different family from the extractor) | Jais or ALLaM (Arabic-centric) | Consensus second opinion, judge |
| Arabic-centric LLM | — | **Jais**, **ALLaM** | Verifier diversity, Arabic generation quality checks |
| Encoder (NER, classification) | — | **CAMeLBERT**, **AraBERT** (fine-tuned) | Person/place NER, block-type classification |
| Embeddings | Commercial embedding APIs (optional) | **BGE-M3** | Semantic index, cross-book similarity |
| Reranker | Commercial rerank API (optional) | **BGE reranker** | Search result reranking |
| Morphology | — | **CAMeL Tools**, **Farasa** | Root, lemma, POS, tokenization |

Version numbers are given only for Anthropic models. For the others, the model family is fixed, and the exact checkpoint is chosen at evaluation time (`eval/` harness) and pinned in config.

**Commercial vs open-weight, per task:**

| Criterion | Commercial wins when | Open-weight wins when |
|---|---|---|
| Quality on classical Arabic | Hard reasoning, few examples | After fine-tuning on our reviewed data |
| Cost | Low volume, hard tasks | High volume, simple tasks |
| Privacy / data control | Client allows external APIs | Client forbids sending text out (open question 6) |
| Latency / throughput | Batch API available | GPU cluster available |
| Reproducibility | Model IDs pinned, but the provider can retire them | Weights fully under our control |

## 4. Routing & cost control

```
unit → rule extractor ──ok──────────────────────────────────▶ score
         │ needs prose understanding
         ▼
       small model (Haiku / small Qwen) ──confidence ≥ 0.80──▶ score
         │ low confidence or sensitive or schema fail
         ▼
       default model (Sonnet / Qwen-mid) + verifier (GPT|Gemini|Jais)
         │ disagreement
         ▼
       judge / Discrepancy Resolver (Opus) ──unresolved──▶ human
```

- **Cache:** key = `sha256(model_id + prompt_id@version + canonical_input)`. Temperature 0. Re-runs cost nothing (EC-016, EC-095).
- **Batching:** one unit + its footnotes per call. Batch API for bulk runs.
- **Budget:** `llm.budget_per_book_usd` in config. When it is exceeded, the remaining work goes to `needs_llm` (EC-112).
- **Gateway:** `llm/gateway.py` is the only place that talks to providers. Providers: `null`, `anthropic`, `litellm`. Switching models is a config change.

## 5. Prompt design

| Rule | How |
|---|---|
| Versioned prompts | Files `llm/prompts/<task>.v<N>.md`. The version is recorded on every output and in `run_manifest.json`. Any change bumps the version. Old outputs remain traceable. |
| Strict grounding | "Use only the text between `<source>` tags. Every fact must include `quote`, copied verbatim from the source. If the text does not state it, return `null`." |
| Structured output | JSON schema generated from the Pydantic genre model, using provider-native structured output / JSON mode. One repair retry on validation error (EC-091). |
| Few-shot | 2–3 verified examples per genre, taken from reviewed units (for the sample: entries #8–#10) |
| Context packaging | Block IDs are given inline (`[b000135] …`), so the model can return block IDs. Offsets are always computed by code, never by the model. |
| Prompt-injection defense | Book text only inside delimited `<source>` data. The system prompt says data is never instructions. There are no tool permissions in the extraction calls. The output is schema- and evidence-validated (EC-067). |
| Origin awareness | Each block is labelled with its `origin`. The model must copy the origin of the evidence block into each fact. |
| Language | Instructions in English. Source in Arabic. Field values stay in Arabic (verbatim) plus optional English normalized enums. |

## 6. Genre extraction schemas

Common envelope for every knowledge unit (see `03-data-contracts.md` for the full models):

```json
{
  "id": "ku_…", "pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6",
  "genre": "biography", "subtype": "ansab", "type": "biographical_entry",
  "origin": "author_text",
  "anchors": [ { "block_id": "b000135", "start": 0, "end": 102, "quote": "…", "block_hash": "sha256:…", "page": 25, "scan_page": 25 } ],
  "payload": { "…genre-specific…": "…" },
  "facts": [ { "predicate": "…", "value": "…", "assertion": "stated|inferred", "origin": "…", "anchors": [ … ] } ],
  "extraction": { "method": "rule|llm|rule+llm", "models": [], "prompt": "biography.v1", "confidence": 0.0, "review_status": "…", "sensitivity": [] }
}
```

### 6.1 Biography / Ansab (sample book — implemented in MVP)

Payload fields: `entry_no`, `person {ism, kunya, laqab, nasab[], nisba, gender}`, `section_id` (family group heading), `group_closure` (e.g. "ابنا أبي هالة"), `tarjama_annotation` (link to the entry's footnote), facts: `converted_to_islam`, `has_narration`, `companion_status` (صحبة), `birth`, `death`, `spouse`, `mother_status` (`umm_walad`), plus relations.

Example (entry #8, verified offsets):

```json
{
  "type": "biographical_entry", "genre": "biography", "subtype": "ansab", "origin": "author_text",
  "anchors": [{"block_id": "b000135", "page": 25, "scan_page": 25, "start": 0, "end": 102}],
  "payload": {
    "entry_no": 8,
    "person": {"ism": "هند", "nasab": ["عتيق", "عابد", "عبد اللَّه", "عمر", "مخزوم"], "gender": "female"},
    "section_heading_block": "b000134",
    "tarjama_annotation": "b000139"
  },
  "facts": [
    {"predicate": "converted_to_islam", "value": true, "assertion": "stated", "origin": "author_text",
     "anchors": [{"block_id": "b000135", "start": 60, "end": 65, "quote": "أسلمت"}]},
    {"predicate": "has_narration", "value": false, "assertion": "stated", "origin": "author_text",
     "anchors": [{"block_id": "b000135", "start": 78, "end": 97, "quote": "ولم يُروَ عنها شيءٌ"}]},
    {"predicate": "sibling_of", "value": "<ent: children of the Prophet ﷺ from Khadija>", "kind": "maternal",
     "assertion": "inferred", "origin": "ai_generated",
     "anchors": [{"block_id": "b000134", "quote": "من أُمهم خديجة"}]}
  ]
}
```

### 6.2 Hadith (sample: takhrij inside editor footnotes — MVP demo)

Payload: `matn` (verbatim), `isnad[] {name, link_word (حدثنا/أخبرنا/عن), position}`, `collector_refs[] {work, volume, page, number}`, `grading {label (sahih|hasan|daif|…), grader, reason}`, `commentary_ref`.
Sensitivity: `prophetic_attribution` (matn) and `hadith_grading` → always review.

Example from `b000228` (p.35, `editor_footnote`):

```json
{
  "type": "hadith_takhrij", "genre": "hadith", "origin": "editor_footnote",
  "payload": {
    "collector_refs": [
      {"work": "المعجم الكبير", "collector": "الطبراني", "volume": 3, "page": 166, "number": 3258,
       "quote": "رواه الطبراني في \"الكبير\" (٣/ ١٦٦) (رقم: ٣٢٥٨)"},
      {"work": "أسد الغابة", "collector": "ابن الأثير", "volume": 2, "page": 55}
    ],
    "grading": {"label": "daif", "grader": "editor (muhaqqiq)", "reason": "لكثرة المجاهيل",
                "quote": "وإسناده ضعيف لكثرة المجاهيل"}
  },
  "extraction": {"sensitivity": ["hadith_grading"], "review_status": "pending_review"}
}
```

### 6.3 Fiqh (design + schema; no sample data)

Payload: `masala` (question), `hukm {label (wajib|mandub|mubah|makruh|haram|sahih|batil|…), text}`, `dalil[] {type (quran|hadith|ijma|qiyas|athar), ref, quote}`, `madhhab`, `qail` (who holds it), `khilaf[] {madhhab|scholar, position, dalil}`, `rajih` (preferred view, *only if the author states it*).
Sensitivity: `fiqh_ruling` → always review. Threshold override 0.95.

### 6.4 Tafsir

Payload: `ayah_ref {surah, ayah_from, ayah_to}` (validated against a Quran index), `ayah_text` (verbatim), `explanation`, `interpretations[] {mufassir, view, quote}`, `qiraat[]`, `asbab_nuzul`, `linked_hadith[]`.
Verse references are validated by programming (surah/ayah exists). Prophetic statements are flagged sensitive.

### 6.5 Seerah

Payload: `event {name, type (battle|treaty|migration|…)}`, `date {hijri, gregorian, precision}`, `place`, `participants[] (entity ids)`, `sequence_hint` (before/after event), `sources_cited[]`.

### 6.6 Aqeedah

Payload: `concept`, `proposition` (verbatim statement), `position {group/school, stance}`, `evidence[] {type, ref, quote}`, `refuted_view`.
Sensitivity: `aqeedah_proposition` → always review.

### 6.7 History (Islamic history)

Payload: `event`, `date {hijri, gregorian, precision}`, `place`, `actors[]`, `chronology_ref` (ordering), `cause/effect` (only if stated), `sources_cited[]`.

### 6.8 Genre Router

Input: `pub.category.name`, title, TOC titles, and a sample of 20 `author_text` blocks. Output: `primary_genre`, `subtype`, `secondary_genres[]`, `evidence`. Sample: category `الأنساب` → `biography/ansab`. Secondary `hadith` because footnotes contain takhrij ("رواه …", "إسناده"). A unit-level override is allowed: a hadith takhrij footnote inside a biography book goes to the hadith extractor.

## 7. Entity recognition, linking & disambiguation

```
blocks ─▶ candidate detection ─▶ nasab parse ─▶ in-book clustering ─▶ authority linking ─▶ disambiguation ─▶ review
          (NER + patterns)       (ism/kunya/     (same entry,        (scholar/narrator     (context, LLM,     (ambiguous,
                                  nasab/nisba)    aliases, gender)     DB, alias index)      dates, teachers)   sensitive)
```

1. **Candidates:** CAMeLBERT NER (production) plus patterns: `بن|ابن|بنت`, `أبو|أم` kunya, entry lines `N - <name>`, headings `* الأُخوة من ولد <name>`.
2. **Nasab parser (`nlp/nasab.py`):** tokens split on `بن/ابن/بنت`, with footnote markers stripped (EC-073) and offsets kept. Output: `{kunya, ism, nasab[], laqab, nisba, gender}`.
3. **In-book clustering:** the entry person, plus their tarjama footnote, plus later mentions with a compatible nasab. Grammar sets gender (ابنا/بنو/بنات).
4. **Authority linking (production):** match against narrator/scholar authority lists (open question 7) on normalized name + kunya + death year + teachers/students. Multiple candidates are never auto-picked (EC-076).
5. **Disambiguation:** score = name similarity × date compatibility × relation compatibility. Below the threshold, or more than one candidate → `ambiguous_entity` + `narrator_disambiguation` (sensitive).
6. **Output:** `entities.json` (canonical name, aliases with anchors, type, gender, death, links) and `relationships.json` (typed relations from DECISIONS §11 with `assertion`, `origin` and anchors).

## 8. Multi-model consensus & confidence

Flow per LLM-extracted unit:
1. Model A (extractor) and Model B (different family) extract independently from the same packaged input.
2. Both outputs pass the schema check and the evidence guard separately.
3. `consensus.py` compares field by field (normalized values, set comparison for lists).
4. If they agree → `agreement ×1.2`. If they disagree → judge (Opus, or the Discrepancy Resolver agent). If resolved → `0.9`. If unresolved → `model_disagreement` → review with both outputs.
5. Confidence formula (DECISIONS §8) → routing (threshold 0.80, or the category override; sensitive categories always go to review).

**Worked example A — rule-based fact (`converted_to_islam`, entry #8):**
`base 0.95 (rule) × evidence 1.0 (exact "أسلمت" at 60–65) × schema 1.0 × agreement 1.0 (single method) × penalties 1.0 = 0.95` → `auto_approved` (not sensitive).

**Worked example B — LLM sibling kind for #9/#10:**
`base 0.75 × evidence 1.0 ("ابنا أبي هالة") × schema 1.0 × agreement 1.2 (A and B both say full siblings) = 0.90` → `auto_approved`.
If Model B said `maternal` instead: judge resolves to `full` → `0.75 × 1.0 × 1.0 × 0.9 = 0.675` → `pending_review`.

**Worked example C — hadith grading (`b000228`):**
`0.95 × 1.0 × 1.0 × 1.0 = 0.95`, but the category is `hadith_grading` (sensitive) → always `pending_review`.

**Calibration:** reviewed samples give a reliability curve per category. Factors and thresholds are tuned in config (EC-105).

## 9. Sensitive-content policy

| Category | Trigger | Policy |
|---|---|---|
| `prophetic_attribution` | Span class `c1`, `قال رسول الله`, hadith matn | Always review. Published only with a source anchor. |
| `hadith_grading` | `صحيح/حسن/ضعيف/موضوع`, `إسناده` | Always review. Grader recorded (author vs editor). |
| `fiqh_ruling` | Hukm field present | Always review. Threshold 0.95 even after review sampling. |
| `aqeedah_proposition` | Aqeedah schema | Always review. |
| `narrator_disambiguation` | Entity link with >1 candidate, or isnad person | Always review. |

Additional rules:
- AI never states a ruling or grading of its own. It only extracts what the text states, attributed to the speaker (`origin`).
- `ai_generated` content is labelled in every output (EC-121).

## 10. Arabic NLP strategy

**Two copies, one truth:** the original text is never changed. A derived `normalized_text` is produced for search and matching only, with a char-index map back to the original (EC-015).

Normalization rules (`nlp/normalize.py`, in order):
1. Unicode NFC.
2. Remove tashkeel/harakat (U+064B–U+0652, U+0670) and Quranic marks (U+06D6–U+06ED).
3. Remove tatweel (U+0640).
4. Alif variants أ إ آ ٱ → ا.
5. ى → ي (search copy). ة → ه (search copy, configurable).
6. ؤ → و, ئ → ي (configurable, search only).
7. Honorific unification: ﷺ ↔ "صلى الله عليه وسلم" ↔ "صلى اللَّه عليه وسلم" → token `<SAW>`. Similar handling for رضي الله عنه / رحمه الله (EC-062).
8. Arabic-Indic digits → ASCII for numeric fields only (`nlp/arabic_digits.py`).
9. "اللَّه" (with shadda) → "الله".
10. Collapse whitespace. Strip footnote markers `(N)` from the search copy, but keep a mapping.

Morphology:
- CAMeL Tools morphological analyzer + disambiguator (MSA/CA models) for lemma, root, POS.
- Farasa as a second segmenter for comparison.
- Example: الأُخوة → lemma أخ, root أ-خ-و. يُروَ (in "ولم يُروَ عنها") → lemma روى, root ر-و-ي.
- The root index enables queries such as "روى" to match يروي / رواية / الرواة.

Search variants: the query goes through the same normalizer. Hybrid retrieval = BM25 on the normalized copy + BGE-M3 vectors, then BGE reranker. Hits are highlighted on the original via the char map (EC-122).

Classical Arabic specifics: no diacritics in most text, long nasab chains, kunya-first naming, same-name narrators, honorific formulas, editor brackets `[…]`, and Hijri dates written in words ("سنةٍ خمسٍ وثمانين وثلاث مئة" → 385, an LLM/number-parser task).

## 11. Model training & fine-tuning

**When:** not in the MVP. Phase 3, after ≥ 2–5k reviewed units per task exist. Before that, prompting + few-shot + RAG over reviewed examples is cheaper and good enough.

| Option | Use when | Not when |
|---|---|---|
| Prompting + few-shot | Start. Every genre. | Volume makes API cost dominant |
| RAG (retrieve similar reviewed units as examples) | Style and edge cases vary by book | — |
| LoRA / QLoRA (PEFT) on open-weight LLM | Stable schema, many reviewed examples, privacy or cost needs | Fewer than ~1k examples per task, or the schema still changing |
| Full fine-tune of an encoder (CAMeLBERT) | NER, block classification | — |
| Full fine-tune of a large LLM | Practically never (cost, forgetting) | — |

**Datasets (per task: NER, unit segmentation, fact extraction per genre, relation, classification):**
1. **Weak supervision:** Shamela structure gives free labels. Headings → section labels. `refs` → annotation links. Entry numbering → unit boundaries. Tarjama footnotes → person mentions.
2. **Distillation:** a large model (Opus/Sonnet) extracts. Only human-approved outputs become training data. Rejected outputs become negative examples.
3. **Reviewer corrections:** every `edited` review item is exported as a corrected pair (EC-103). This is active learning: low-confidence items are reviewed first, so they enter the training data first.
4. **Gold (test only):** printed indexes (PDF pp. 76–80 sample → `eval/gold_index_sample.json`) and expert-annotated books. **Never** used for training.
5. **Split:** book-level (a book is entirely in train or entirely in test). Stratified by genre and century. Test books are frozen.
6. **Annotation guidelines:** a document per genre with examples, especially for origin (author vs editor), assertion (stated vs inferred) and sibling kind.

**Recipe (Phase 3):**
- Base: Qwen instruct (7–32B) or Jais / ALLaM. Pick by Arabic eval score on our dev set.
- Method: QLoRA (4-bit base) with PEFT + TRL `SFTTrainer`. LoRA rank r = 16–64, alpha = 2r, dropout 0.05, lr 1e-4–2e-4, 2–3 epochs, max seq 4–8k. Target attention + MLP projections.
- Output format: the same JSON schema as the prompts, so swapping the model changes nothing downstream.
- Serving: vLLM with multi-LoRA (one base model, one adapter per genre/task, selected per request by the router).
- Infra: 1–2 × A100/H100 80GB for QLoRA training. 1 × GPU per serving replica. Experiment tracking via MLflow or W&B.

**Evaluation metrics:**
- Entity F1
- Relation F1
- Fact-level precision/recall
- **Evidence accuracy** (quote found at the anchor)
- Schema validity rate
- Human approval rate
- Calibration error
- Cost per 1k units

The fine-tuned model must match or beat the commercial baseline on the frozen test books before it is routed traffic.

**When NOT to fine-tune:** data is too little or too noisy; the schema is still changing; the task is solvable by rules; a commercial model is already cheap enough at the current volume; or legal constraints apply to the training text.
