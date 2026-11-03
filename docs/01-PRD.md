# PRD — AI-Powered Islamic Digital Library: Post-OCR Enrichment Platform

| Field | Value |
|---|---|
| Status | Draft v1.0 (assignment submission) |
| Source requirement | Client technical assignment brief, §1–§8 (not included in this repository) |
| Names / values | `docs/DECISIONS.md` (binding) |
| Coverage proof | `docs/09-coverage-matrix.md` |
| Roadmap | `docs/08-roadmap.md` |

---

## 1. Problem

The client operates a digital library with thousands of Islamic books, mainly in Arabic, with some in other languages. The books are already digitized: the sample book arrives as structured JSON (from Shamela) together with the scanned PDF. In this form the books can be read, but they cannot be explored as knowledge. A reader cannot ask "who are the siblings of Hind ibn Abi Hala?", "which books cite al-Isaba for this person?", or "where is this ruling discussed across commentaries?".

The client wants every book to be enriched automatically with structured metadata, indexes, annotation links, knowledge units, entities and relationships. The enrichment must be:
- stored separately from the untouched original,
- traceable to the exact source location,
- clear about what the author said versus what the AI inferred,
- confidence-scored and approved by humans where necessary.

## 2. Background (sample input)

- **Book:** *الإخوة والأخوات*, by al-Daraqutni (d. 385 AH), edited (tahqiq) by Basim al-Jawabira. Published by Dar al-Raya, 1413 AH / 1993.
- **Reference:** `pub_ref = pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6`.
- **Files:** `data/demo_book_daraqutni.json` (Shamela source, schema 3.0, adapter 1.3.0) and `data/demo_book_daraqutni_v1.pdf` (80 scanned pages, no text layer).
- **Verified facts:** see DECISIONS.md §7.

## 3. Goals

| ID | Goal |
|---|---|
| G1 | Turn a digitized book into a linked enrichment layer: metadata, structure, annotations, citations, knowledge units, entities, relationships, indexes. |
| G2 | Never modify original content. Every enrichment record points back to it through verifiable anchors. |
| G3 | Separate author statements, transmitter/editor text and AI-generated content. |
| G4 | Make every AI output confidence-scored, cross-checked and routable to human review. Sensitive religious content is always reviewed. |
| G5 | Adapt to change: new source formats via adapters, new genres via schema plugins, new models via the gateway, new revisions via anchor re-validation. |
| G6 | Scale from one book (MVP) to thousands (production) with the same step contracts. |
| G7 | Deliver the assignment artefacts: diagrams, technology list, model strategy, extraction approach, training approach, MVP and roadmap. |

## 4. Non-goals

- **OCR and initial digitization.** A separate team owns these. We consume their output, or the Shamela JSON, as is.
- **Editing, correcting or re-typesetting** the original text.
- **Issuing religious verdicts** or presenting AI interpretations as scholarly statements.
- **A full production deployment** within the 1–2 day assignment. Production is designed and backlogged (Epic E16).
- **A reader-facing UI.** Only APIs, exports and a minimal review viewer are in scope.

## 5. Users and personas

| Persona | Needs | Touchpoints |
|---|---|---|
| **Library editor** (publishing team) | Ingest books, see quality issues, publish approved enrichment | CLI/API, `document_report.json`, `validation_report.json` |
| **Scholar reviewer** (subject-matter expert) | Check uncertain or sensitive outputs against the source text and approve, edit or reject them | Review queue (JSON + HTML in MVP, Argilla in production) |
| **Reader / researcher** | Search and navigate across books, people and citations, then jump to the source page | Search API, `search_index.json`, publishing API (production) |
| **Ops / ML engineer** | Run, monitor and reprocess pipelines; manage cost, models and prompts | `run_manifest.json`, logs, config, Prefect (production) |
| **Coding agent** | Implement tickets without needing further decisions | `docs/` (this folder), tickets with acceptance criteria |

## 6. Assumptions and open questions

Assumptions (A) are used until the client answers. The open questions (Q) below have been sent to the client.

| ID | Assumption / question | Impact if wrong |
|---|---|---|
| A1 / Q1 | Submission is a Markdown/PDF proposal plus a repo (`deliverables/` and the code at the repository root) | Repackaging only |
| A2 / Q2 | Deadline is 1–2 days, with a possible walkthrough | Scope of MVP |
| A3 / Q3 | Block IDs (`b000135`) are stable within a revision. Across revisions they may change, so ADR-017 re-validates anchors by `block_hash`. | Anchor strategy |
| Q3b | Meaning of span classes `c1`–`c5`. Inferred so far: c2 = footnote marker, c5 = emphasis, c1 = Prophetic speech, c4 = editor bracket heading. | Sensitivity detection uses c1 only as a hint |
| **Q-HASH** | **Which method produces `content_sha256`?** We could not reproduce it with three canonicalizations. Until answered, it is stored as `source_declared_hash`, `verified: false` (issue `source_hash_unverified`). | Integrity proof relies on our own hashes (ADR-017) |
| A4 / Q4 | The printed indexes (PDF pp. 73–80) may be used as a gold sample for evaluation | Evaluation method |
| A5 / Q5 | Other sources (OCR team, other archives) will use other formats, so each one gets an adapter | Adapter count |
| A6 / Q6 | Commercial LLM APIs are allowed for the demo. The MVP also runs fully without any key (`null` provider). | Privacy design |
| A7 / Q7 | No existing client schema or authority database, so we propose our own | Contract alignment |
| A8 / Q8 | Scale: about 10,000 books, about 3M pages, about 500 new books per month | Infrastructure sizing (roadmap) |
| A9 / Q9 | 2–4 scholar reviewers are available part-time | Review queue prioritisation |
| A10 | Arabic first. English/Urdu/Persian/Bangla translations are later, with the same pipeline and language-specific NLP. | NFR-009 |

---

## 7. Functional requirements

Priority: **P0** = MVP must, **P1** = MVP should, **P2** = production.
Column **MVP?**: **Built** = implemented and tested in this repository; **Designed** = specified with a production backlog ticket.

### 7.1 Ingestion and source adapters

**FR-001 — Ingest a book package.** Accept the book JSON, the PDF and identifiers (`pub_id`, `work_id`, `edition_id`, revision).
- Rationale: assignment §4 step 1.
- Priority / MVP: P0 / Built.
- Acceptance: `ilm-engine run --input data/demo_book_daraqutni.json` (PDF located via `_meta.scan.saved_file`, or `--pdf`) loads both files. `pub_ref` resolves to `pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6`. The PDF page count (80) is recorded.
- Source: §4.1, §7.

**FR-002 — Adapter registry.** Select the adapter by `(source_code, schema_version)`, e.g. `(src-shamela, 3.0)` → `ShamelaV3Adapter`. An unknown pair fails closed with `unknown_schema_version`; nothing is guessed.
- Rationale: JSON formats will change, and new sources will appear.
- Priority / MVP: P0 / Built.
- Acceptance: a registry unit test covers the known pair → adapter and the unknown pair → error plus issue. Adding an adapter requires no change outside `adapters/`.
- Source: §6 modular, §3.1.

**FR-003 — Canonical book schema.** The adapter outputs a versioned `CanonicalBook` (pages, blocks, refs, spans, markers, `continues`, metadata_raw). Unknown source fields are preserved in `raw_extras`.
- Priority / MVP: P0 / Built.
- Acceptance: the golden-file test (`tests/golden/`) gives byte-identical canonical output; 594 blocks and 68 pages; `raw_extras` is non-empty for unmapped keys.
- Source: §3.1, §3.2.

**FR-004 — Adapter contract tests.** Every adapter ships a golden input/output pair. CI fails on drift.
- Priority / MVP: P1 / Built.
- Acceptance: changing a mapping without updating the golden file fails `pytest`.
- Source: §6 repeatable.

### 7.2 Integrity and immutability

**FR-010 — Read-only originals.** Originals are copied to `store/originals/<pub_ref>/` with hashes. The pipeline never writes to `data/` or to the store copy.
- Priority / MVP: P0 / Built.
- Acceptance: invariant test — the sha256 of every file in `data/` is identical before and after a run.
- Source: §1, §6.

**FR-011 — Block and content hashes.** Compute `block_hash` per block and `canonical_content_hash` per book (DECISIONS §5). Store the source `content_sha256` as `source_declared_hash`, `verified: false`.
- Priority / MVP: P0 / Built.
- Acceptance: 594 block hashes; issue `source_hash_unverified` raised once.
- Source: §6.

**FR-012 — Stale-anchor detection.** When a new revision arrives, re-validate every anchor's `block_hash`. Mismatches become `anchor_stale`, and only the changed blocks are reprocessed.
- Priority / MVP: P1 / Built (simulated r7 fixture).
- Acceptance: a modified fixture block produces exactly one stale anchor set and one reprocess task.
- Source: §6 repeatable/scalable.

### 7.3 A. Metadata extraction

**FR-020 — Bibliographic metadata.** Extract title, author (name, kunya, death date), editor, publisher, edition, year (Hijri and Gregorian), volumes, pages and category. Each field carries `provenance` (`source_metadata` | `book_content` | `ai_generated`) and an anchor where applicable.
- Priority / MVP: P0 / Built.
- Acceptance: the author's death of 385 AH is anchored to `b000049` (p.9); the editor is "باسم فيصل أحمد الجوابرة"; the year is 1413/1993.
- Source: §2A.1.

**FR-021 — Front/back matter mining.** Find metadata-relevant statements in the preface, introduction, colophon and closing pages, such as manuscript description, attribution proof and transmission chain.
- Priority / MVP: P1 / Built (rules + optional LLM).
- Acceptance: the "صحة نسبة الكتاب" section is linked as attribution evidence; the manuscript title page (p.17) is captured as `transmission_isnad`.
- Source: §2A.2.

**FR-022 — Missing / inconsistent metadata.** Detect conflicts and gaps: page count claimed vs held, title spelling variants (الإخوة / الأُخوة), the author name with "بن مهدي" on p.17 but not on the card, and TOC entries without a block.
- Priority / MVP: P0 / Built.
- Acceptance: the issues `page_count_mismatch` (explained as non-content pages 1, 2, 4, 18), `title_variant`, `metadata_conflict` and `toc_without_block` are present with evidence.
- Source: §2A.3.

### 7.4 B. Book family and relationship mapping

**FR-030 — Work identity.** Distinguish the *work* (the abstract book) from its *edition* and *publication*, using `work_id`, `edition_id` and `pub_id`.
- Priority / MVP: P0 / Built.
- Acceptance: `metadata.json` has the `work`, `edition` and `publication` levels.
- Source: §2B.1.

**FR-031 — Related works detection.** Detect related and fundamental works mentioned in the book: works cited in footnotes (الإصابة, أسد الغابة, …) and same-topic works named in the preface (e.g. Abu Dawud's "الأخوة الذين روي عنهم الحديث", in `b000018`). Store them as `wrk_*` with relations `cites` / `same_topic_as`.
- Priority / MVP: P0 / Built.
- Acceptance: at least 10 distinct cited works with counts (الإصابة 145, …); at least one `same_topic_as` relation anchored to `b000018`.
- Source: §2B.1, §4.4.

**FR-032 — Work relation types.** Support `sharh_of`, `hashiyah_of`, `mukhtasar_of`, `translation_of`, `edition_of`, `tahqiq_of`, `cites` and `same_topic_as`, with direction and evidence.
- Priority / MVP: P1 / Built (schema + `tahqiq_of`, `cites`, `same_topic_as` on the sample); others are Designed.
- Acceptance: schema validation; the sample has `tahqiq_of` (edition by al-Jawabira).
- Source: §2B.2.

**FR-033 — Cross-book section alignment.** Map corresponding sections and blocks between a matn and its sharh/hashiyah (e.g. the sharh quotes the matn passage, then comments). Approach: quote detection plus embedding similarity plus LLM confirmation.
- Priority / MVP: P2 / Designed.
- Acceptance (production): on a matn+sharh pair, at least 90% of matn sections are aligned on a reviewed sample.
- Source: §2B.3, §2G.2.

### 7.5 C. Deep indexing and segmentation

**FR-040 — Structural hierarchy.** Build book → volume → section → subsection from `heading`/`toc_heading` blocks and the TOC. Align the TOC with Shamela `source_ref.key` (the offset varies 2→3→4).
- Priority / MVP: P0 / Built.
- Acceptance: all 17 TOC entries are matched to blocks or flagged; every block belongs to exactly one section.
- Source: §2C.1.

**FR-041 — Paragraph and knowledge-unit segmentation.** Segment text into paragraphs (blocks) and knowledge units. The sample has 75 biographical entries, including several per block and mid-sentence entries (#32 in `b000294`).
- Priority / MVP: P0 / Built.
- Acceptance: 75/75 entries numbered 1–75, with no false `numbering_gap`.
- Source: §2C.3.

**FR-042 — Topic and semantic indexes.** Produce a topic index (people, tribes/lineages, places, cited works, hadith) and a semantic index (embeddings per unit).
- Priority / MVP: P1 / Built (topic/lexical); semantic is optional and Designed.
- Acceptance: `search_index.json` lists every entity, with the anchors where it appears.
- Source: §2C.2, §4.5.

**FR-043 — Structural pattern plugins.** Handle different structural patterns (numbered tarajim, kitab/bab/fasl, ayah-by-ayah tafsir, hadith numbering, matn+sharh interleaving) through pattern configurations per genre.
- Priority / MVP: P1 / Built (numbered tarajim); the others are Designed as config.
- Acceptance: the pattern is selected from genre/config; a new pattern needs no core change.
- Source: §2C.4.

### 7.6 D. Arabic NLP and search enhancement

**FR-050 — Normalization (derived).** Search normalization: strip tashkeel and tatweel, unify alif forms, ى/ي, ة/ه, normalize honorifics (ﷺ ↔ صلى الله عليه وسلم), convert Arabic-Indic digits. The original text is never overwritten.
- Priority / MVP: P0 / Built.
- Acceptance: "الدَّارقطني", "الدارقطني" and "الدَّارَقُطْنِيّ" share one normalized key; the original text is unchanged.
- Source: §2D.1, §2D.5.

**FR-051 — Morphology, root, lemma.** Produce a morphological analysis with root and lemma per token (CAMeL Tools when installed; otherwise a light stemmer flagged `approximate`).
- Priority / MVP: P1 / Built (optional dependency).
- Acceptance: with CAMeL installed, "الأُخوة" maps to root أخو.
- Source: §2D.2.

**FR-052 — Entity recognition and disambiguation.** Recognize persons (via nasab parsing), places, tribes, works and dates. Disambiguate same-name persons using lineage, section context and footnote evidence; anything ambiguous goes to `ambiguous_entity`.
- Priority / MVP: P0 / Built.
- Acceptance: two persons named "هند" in the Khadija section are distinct entities (entry 8, a female; entry 9, a male, son of Abu Hala).
- Source: §2D.3.

**FR-053 — Semantic search and contextual retrieval.** Hybrid lexical + vector retrieval over units and blocks. Results return anchors.
- Priority / MVP: P1 / Built (lexical); vector optional and Designed (OpenSearch + Qdrant).
- Acceptance: the query "هالة" returns entry 10 with its anchor.
- Source: §2D.4.

### 7.7 E. Annotation mapping

**FR-060 — Footnote linking.** Resolve `refs` (text span → footnote block). Join `continues` footnotes across pages. Link nested footnotes (a footnote of a footnote) by marker.
- Priority / MVP: P0 / Built.
- Acceptance: 300/300 refs resolve; 16 continuations joined; `b000215` is linked to `b000210` via marker "أ" and flagged `nested_footnote` for review.
- Source: §2E.1, §2E.2.

**FR-061 — Endnotes and sidenotes.** The canonical schema supports annotation types `footnote`, `endnote`, `sidenote` and `marginal_gloss`, with position. Adapters map the source equivalents.
- Priority / MVP: P1 / Built (schema; the sample has only footnotes).
- Acceptance: schema test with a synthetic endnote fixture.
- Source: §2E.1.

**FR-062 — Internal references.** Detect in-book cross references ("ترجمة رقم (٣٣)", "كما سيأتي", "تقدم") and resolve them to the target unit or section. Unresolvable ones become `unresolved_internal_ref`.
- Priority / MVP: P0 / Built.
- Acceptance: "ترجمة رقم (٣٣)" (p.11, `b000063`) links to entry 33.
- Source: §2E.1.

**FR-063 — External citations.** Parse the work cited plus the volume/page (`"الإصابة" (٨/ ١٥٧)`) into `cit_*` records linked to `wrk_*`.
- Priority / MVP: P0 / Built.
- Acceptance: the counts match DECISIONS §7 within ±2 per work.
- Source: §2E, §2B, §2G.

### 7.8 F. Genre-specific knowledge extraction

**FR-070 — Genre router.** Classify the primary and secondary genre from the category, front matter and content signals. The sample gives `biography/ansab` as primary and `hadith` (takhrij in footnotes) as secondary.
- Priority / MVP: P0 / Built.
- Acceptance: the sample is classified correctly, with evidence.
- Source: §2F, §4.4.

**FR-071 — Genre schema plugins.** Seven schemas: fiqh (mas'ala, hukm, dalil, madhhab, qa'il, khilaf), hadith (matn, isnad, narrators, grading, takhrij, sharh_ref), tafsir (ayah ref, explanation, interpretations, mufassir), seerah (event, persons, date, place), aqeedah (concept, proposition, evidence), history (event, persons, chronology, place), biography (person, nasab, kunya, laqab, nisba, birth, death, teachers, students, relatives).
- Priority / MVP: P0 / Built (schemas plus biography and hadith-takhrij extractors); the others are Designed with fixtures.
- Acceptance: all seven schemas validate example JSON; biography produces 75 units.
- Source: §2F table.

**FR-072 — Source retention.** Every unit and fact keeps its anchors (book, revision, page, scan page, block, offsets, quote).
- Priority / MVP: P0 / Built.
- Acceptance: 100% of facts carry anchors, and every `text[start:end] == quote`.
- Source: §2F last sentence, §6.

**FR-073 — Hadith takhrij in footnotes.** Extract the hadith source (collection, number) and any grading statement ("وإسناده ضعيف", `b000228`). Grading is `sensitive_content` and always goes to review.
- Priority / MVP: P1 / Built.
- Acceptance: the `b000228` grading is in the review queue with category `hadith_grading`.
- Source: §2F Hadith.

### 7.9 G. Knowledge graph and cross-book mapping

**FR-080 — Entities and relationships.** Entities: persons, works, places, tribes, events, concepts, rulings, references. Relationships: as listed in DECISIONS §11, e.g. `sibling_of` with `kind` full/paternal/maternal/unknown.
- Priority / MVP: P0 / Built.
- Acceptance: entries 9 and 10 are `sibling_of` (full, "ابنا أبي هالة"). "لأم ولد" is never mapped to maternal.
- Source: §2G.1.

**FR-081 — Sibling group detection.** Detect group-closing phrases ("ابنا …", "بنو …", "وأختهم") so the members of a group are linked. Grammar mismatches (e.g. dual "ابنا" applied to three people) are penalised.
- Priority / MVP: P0 / Built (rules + `needs_llm` fallback).
- Acceptance: "بنو عبد المطلب" closes the group of entries 18–21.
- Source: §2G.1.

**FR-082 — Cross-book linking.** Link the same entity across books (authority IDs, alias tables, embeddings) and link knowledge units across books.
- Priority / MVP: P2 / Designed (MVP exports graph-ready nodes/edges).
- Acceptance (production): entity resolution precision of at least 0.95 on a reviewed sample.
- Source: §2G.2.

**FR-083 — Discovery export.** Export nodes and edges (JSON + optional `graph.html`). In production the export goes to Neo4j.
- Priority / MVP: P1 / Built.
- Acceptance: the graph opens and every edge has an anchor.
- Source: §2G.3.

### 7.10 Validation (multi-model, confidence, discrepancy)

**FR-090 — Evidence guard.** Every LLM fact must include a verbatim quote that is found in the cited block. If it is not found, the fact is rejected with `evidence_not_found`.
- Priority / MVP: P0 / Built.
- Acceptance: a unit test with a fabricated narrator is rejected.
- Source: §3.7, §6.

**FR-091 — Multi-model consensus.** Two independent models (different families) extract; a field-level comparison follows; a judge resolves disagreements; anything still unresolved becomes `model_disagreement` and goes to review.
- Priority / MVP: P1 / Built (works with `null` + rules; real models when keys exist).
- Acceptance: a fixture with disagreeing outputs produces a review item; the system never picks one value silently.
- Source: §3.7.

**FR-092 — Confidence scoring.** Use the formula in DECISIONS §8. The LLM's self-reported confidence is ignored.
- Priority / MVP: P0 / Built.
- Acceptance: unit tests per factor; the threshold comes from config.
- Source: §3.7, §6.

**FR-093 — Rule validation.** Checks: schema, anchor validity, numbering continuity (re-checked by a second parser before flagging), grammar/gender agreement, page/TOC consistency.
- Priority / MVP: P0 / Built.
- Acceptance: there is no `numbering_gap` on the sample, and a synthetic gap fixture raises one.
- Source: §4.9.

### 7.11 Human review

**FR-100 — Review routing.** Route an item to review when confidence is below its threshold, when it is sensitive (`prophetic_attribution`, `hadith_grading`, `fiqh_ruling`, `aqeedah_proposition`, `narrator_disambiguation`), or on any blocking issue.
- Priority / MVP: P0 / Built.
- Acceptance: every sensitive item is `pending_review` regardless of score.
- Source: §3.8, §4.10.

**FR-101 — Review item content.** Each item shows the original text, the extracted value, the anchors (with the PDF page), model A/B outputs, confidence, issues and suggested action.
- Priority / MVP: P0 / Built (`review_queue.json` + static HTML viewer).
- Acceptance: the HTML lists items with the source quote highlighted.
- Source: §3.8.

**FR-102 — Review actions and audit.** Reviewers can approve, reject, edit or request reprocessing. Every action is stored with reviewer, timestamp, before/after and reason. Approved edits become training data.
- Priority / MVP: P1 / Built (a decisions file applied by CLI `ilm-engine review apply`); Argilla is Designed.
- Acceptance: applying a decisions file updates the statuses and writes an audit log.
- Source: §3.8, §3.9.

### 7.12 Storage, publishing and search

**FR-110 — Enrichment layer storage.** Store approved (and pending) records separately from the originals: JSON files plus SQLite in the MVP, PostgreSQL in production, with derived stores Qdrant, Neo4j and OpenSearch.
- Priority / MVP: P0 / Built.
- Acceptance: `enrichment.db` tables match the data contracts; derived stores can be rebuilt from the source of truth.
- Source: §3.6, §4.11.

**FR-111 — Publishing outputs.** The consolidated `enrichment.json` plus per-aspect files (DECISIONS §10) are what publishing consumes. Production adds a FastAPI publishing and search API.
- Priority / MVP: P0 / Built (files); the API is Designed.
- Acceptance: all 17 output files are produced deterministically (two runs give identical hashes).
- Source: §4.12.

**FR-112 — Reader jump-to-source.** Every published fact resolves to the PDF page (`scan_page`) and block. Character-level linking applies to the JSON text; the PDF has no text layer, so linking there is page-level.
- Priority / MVP: P1 / Built.
- Acceptance: the anchor for entry 8 resolves to PDF page 25.
- Source: §6 traceable.

### 7.13 Orchestration, AI models, training

**FR-120 — Pipeline orchestration.** Steps run as an idempotent, cached DAG with retries and a run manifest. In production they map 1:1 to Prefect tasks.
- Priority / MVP: P0 / Built.
- Acceptance: rerunning hits the cache; a failed step can be resumed.
- Source: §3.3.

**FR-121 — LLM gateway.** A provider-agnostic interface (null / anthropic / litellm) with versioned prompts, temperature 0 and a response cache.
- Priority / MVP: P0 / Built.
- Acceptance: the pipeline completes with `null`; switching provider is a config change only.
- Source: §3.3, §3.4.

**FR-122 — Agents only where needed.** Four agents: Genre Router, Genre Extractor, Related-Works/Citation Resolver, Discrepancy Resolver. Everything else is deterministic.
- Priority / MVP: P1 / Built (as functions behind the agent interface); LangGraph is Designed.
- Acceptance: the docs table shows Programming / NLP / LLM / Agent per task.
- Source: §3.3, §3 last line.

**FR-123 — Training data capture.** Persist reviewer-approved and edited items as labelled examples (task, input, gold output, anchors) for fine-tuning.
- Priority / MVP: P1 / Built (export `training_examples.jsonl`); QLoRA training is Designed.
- Acceptance: the export contains only approved or edited items, with a book-level split key.
- Source: §3.9, §5.6.

### 7.14 Deliverables

**FR-130 — Assignment deliverables.** `deliverables/Technical_Proposal.md` (+ PDF), the System Architecture diagram, the Automation & Data-Flow diagram, technology recommendations, the Arabic NLP & model strategy, the knowledge extraction approach, the training approach, the MVP report with real numbers, and the roadmap.
- Priority / MVP: P0 / Built.
- Acceptance: every §5 item is present, checked against `09-coverage-matrix.md`.
- Source: §5.1–5.8.

---

## 8. Non-functional requirements

| ID | Requirement | Measure / acceptance | Source |
|---|---|---|---|
| NFR-001 | **Immutability**: original content is never modified | Before/after file hashes are equal; the pipeline has no write path to originals; production uses S3 object lock | §1, §6 |
| NFR-002 | **Traceability**: every unit, fact and annotation is traceable | 100% have ≥1 anchor; 100% of anchors verify (`quote` match + `block_hash`) | §2F, §6 |
| NFR-003 | **Origin separation** | 100% of records carry `origin` + `assertion`; inferred facts are always `ai_generated` | §6 |
| NFR-004 | **Modularity / adaptability** | New adapter, genre schema, model provider or store = new plugin + config, with no core edit (verified by code review checklist) | §6, §3.1 |
| NFR-005 | **Repeatability / determinism** | Same input + config + model/prompt version gives byte-identical outputs; deterministic IDs; temperature 0 + cache; manifest records versions | §6 |
| NFR-006 | **Scalability** (assumption A8) | Production: 10k books, about 3M pages; target throughput 500 books/day with horizontal workers; per-book parallelism by section; incremental reprocessing by block hash | §6, §3.1 |
| NFR-007 | **Cost control** | Rules before NLP before LLM; small model first, escalation for hard cases; batch APIs; cache. Target below US$0.50 per 100 pages in production (assumption, see roadmap) | §3.4 |
| NFR-008 | **Privacy / data residency** | Provider allow-list in config; open-weight self-hosted option (vLLM) for restricted books; no data sent when provider is `null` | §3.4 |
| NFR-009 | **Languages** | Arabic first; language detected per block; the NLP pipeline is pluggable per language; other-language books reuse all non-NLP steps | §1 |
| NFR-010 | **Observability** | `run_manifest.json`, structured logs, per-step timings, LLM token/cost counters; production uses OTel + Grafana + Langfuse | §3.3 |
| NFR-011 | **Review UI accessibility** | RTL rendering, Arabic fonts, keyboard navigation, source highlighting, works offline (static HTML in the MVP) | §3.8 |
| NFR-012 | **Security** | Secrets only via env vars; no keys in the repo; audit log for review actions; role-based access in production | §3.8 |
| NFR-013 | **Performance (MVP)** | The sample book processes in under 60 s without LLM on a laptop | — |
| NFR-014 | **Quality gates** | `uv run pytest`, `ruff check` clean; golden tests; Definition of Done in DECISIONS §13 | §6 |

---

## 9. Success metrics

| Metric | Target (sample book) | Target (production) |
|---|---|---|
| Biographical entries detected | **75/75** (1–75, no false gap) | — |
| Footnote refs resolved | **300/300** | ≥ 99.5% |
| Continued footnotes joined | **16/16** | — |
| Nested footnote linked | `b000215` → `b000210` | — |
| TOC entries aligned or flagged | **17/17** | 100% |
| Anchors verifying (`quote` + hash) | **100%** | 100% |
| Records with `origin` | **100%** | 100% |
| Person entity precision / recall vs printed index sample (فهرس الرواة) | ≥ 0.90 / ≥ 0.85 | ≥ 0.95 / ≥ 0.90 after fine-tuning |
| Sensitive items routed to review | **100%** | 100% |
| Auto-approve rate (non-sensitive) | reported | 70–85% after calibration |
| Reviewer approval rate of auto-approved sample audit | — | ≥ 97% |
| Determinism | 2 runs give identical output hashes | same |
| Runtime without LLM | < 60 s | 500 books/day |

## 10. Release plan

| Release | Content | Exit criteria |
|---|---|---|
| **MVP (assignment, 1–2 days)** | Epics E00–E15: adapter, integrity, structure, origin, metadata, annotations, citations, units, entities, relations, LLM gateway (null + optional real), validation, review queue, JSON + SQLite, lexical search, evaluation, CLI, deliverables | All P0 acceptance criteria pass; success metrics reported in `deliverables/` |
| **Phase 1 — Core platform** | Postgres, MinIO, Prefect, Argilla, FastAPI, second adapter (OCR team format) | 100 books processed and reviewed end-to-end |
| **Phase 2 — Extraction at depth** | All seven genre extractors, Neo4j, OpenSearch + Qdrant hybrid search, multi-model consensus in production | Genre F1 targets on gold sets |
| **Phase 3 — Scale & adapt** | QLoRA models on vLLM, cost optimisation, thousands of books | Cost and throughput NFRs met |
| **Phase 4 — Cross-book discovery** | Book families, sharh alignment, cross-book entity graph, discovery UI | FR-033 / FR-082 targets |

Details: `08-roadmap.md`.
