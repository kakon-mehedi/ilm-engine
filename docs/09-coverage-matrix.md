# Coverage Matrix — Assignment → Requirements → Decisions → Tickets

This file shows that every line of the client's technical assignment brief is covered.

**How to read it**
- **Status:** **Built** = implemented and tested in this repository. **Designed** = specified in the docs, with a production backlog ticket (E16).
- **ADR:** files in `adr/`.
- **Tickets:** files in `tickets/`.
- **Doc:** section files in `docs/`: 01 = PRD, 02 = architecture, 03 = data contracts, 04 = edge cases, 06 = AI strategy, 07 = test plan, 08 = roadmap.

**Result: 100% of the assignment lines are mapped. None is uncovered.** §10 sums this up.

---

## §1 Project overview and scope

| # | Assignment line | FR / NFR | ADR | Doc | Tickets | Status |
|---|---|---|---|---|---|---|
| 1.1 | Automated publishing and knowledge enrichment system for thousands of Islamic books in Arabic and other languages | G1, G6, NFR-006, NFR-009 | ADR-002, ADR-004 | 01 §1, 02 | T-001–T-004, T-140–T-143, T-160–T-169 | Built (1 book) / Designed (scale) |
| 1.2 | Process digitized books, enrich with structured metadata, detailed indexes, annotations, knowledge units, relationships | FR-020–FR-083 | ADR-001 | 01 §7 | T-030–T-084 | Built |
| 1.3 | Make contents more discoverable and interconnected | FR-042, FR-053, FR-083, FR-111 | ADR-005 | 02 | T-120–T-122, T-112 | Built (lexical, graph export) / Designed (hybrid search) |
| 1.4 | OCR / digitization handled by a separate team (out of scope) | Non-goals | ADR-002 | 01 §4 | T-010 (adapter consumes OCR output) | Built |
| 1.5 | Focus on post-OCR processing, AI automation, knowledge extraction, publishing workflows | FR-001–FR-123 | ADR-004, ADR-014 | 02 | E01–E14 | Built |
| 1.6 | Original book content must remain unchanged | FR-010, NFR-001 | ADR-001, ADR-017 | 03 §integrity | T-020–T-023 | Built |
| 1.7 | Additional information kept in a separate structured enrichment layer, linked to the content | FR-110, FR-072, NFR-002 | ADR-001, ADR-003 | 03 | T-110–T-113, T-021 | Built |

## §2 Key functional requirements

### A. Metadata extraction

| # | Line | FR | ADR | Tickets | Status |
|---|---|---|---|---|---|
| A.1 | Extract title, author, editor, publisher, edition, year and other bibliographic info | FR-020, FR-030 | ADR-010 | T-040 | Built |
| A.2 | Identify relevant info from prefaces, introductions, concluding pages and other sections | FR-021 | ADR-007, ADR-010 | T-041, T-034 | Built |
| A.3 | Identify missing or inconsistent metadata | FR-022 | ADR-008 | T-042, T-030 | Built |

### B. Book family and relationship mapping

| # | Line | FR | ADR | Tickets | Status |
|---|---|---|---|---|---|
| B.1 | Identify original/fundamental books and related works | FR-030, FR-031 | ADR-018 | T-053, T-084 | Built |
| B.2 | Map commentary (Sharh), supercommentary (Hashiyah), translation, summary, explanation | FR-032 | ADR-018 | T-084, T-163 | Built (schema + sample relations) / Designed (multi-book) |
| B.3 | Hierarchical relationships; map corresponding sections/blocks across books | FR-032, FR-033 | ADR-018, ADR-003 | T-163 | Designed |

### C. Deep indexing and segmentation

| # | Line | FR | ADR | Tickets | Status |
|---|---|---|---|---|---|
| C.1 | Identify books, volumes, chapters, subchapters, sections | FR-040 | ADR-002 | T-031, T-032 | Built |
| C.2 | Generate topic-based and semantic indexes | FR-042 | ADR-005, ADR-012 | T-120, T-121 | Built (topic) / optional (semantic) |
| C.3 | Segment content into paragraphs and knowledge units | FR-041 | ADR-013 | T-070, T-071 | Built |
| C.4 | Support different structural patterns across Islamic literature | FR-043 | ADR-013 | T-072, T-094 | Built (tarajim) / Designed (other patterns as config) |

### D. Arabic NLP and search enhancement

| # | Line | FR | ADR | Tickets | Status |
|---|---|---|---|---|---|
| D.1 | Arabic normalization and diacritic handling | FR-050 | ADR-012 | T-060 | Built |
| D.2 | Morphological analysis, root identification, lemmatization | FR-051 | ADR-012 | T-062 | Built (optional CAMeL) |
| D.3 | Entity recognition and disambiguation | FR-052 | ADR-008 | T-063, T-080, T-082 | Built |
| D.4 | Semantic search and contextual retrieval | FR-053 | ADR-005 | T-120–T-122 | Built (lexical) / Designed (hybrid vector) |
| D.5 | Handle classical Arabic and variations in spelling and terminology | FR-050, FR-052 | ADR-012 | T-060, T-061 | Built |

### E. Annotation mapping

| # | Line | FR | ADR | Tickets | Status |
|---|---|---|---|---|---|
| E.1 | Identify and map footnotes, endnotes, sidenotes, internal references | FR-060, FR-061, FR-062, FR-063 | ADR-002, ADR-003 | T-050, T-051, T-052, T-054 | Built (footnotes, internal refs) / Built-schema (endnote, sidenote) |
| E.2 | Link annotations to their text locations | FR-060, FR-072 | ADR-003 | T-050 | Built |

### F. Genre-specific knowledge extraction

| # | Line | FR | ADR | Tickets | Status |
|---|---|---|---|---|---|
| F.0 | Design dynamic extraction approaches for different types of literature | FR-070, FR-071 | ADR-013, ADR-014 | T-093, T-094 | Built (router + plugins) |
| F.1 | Fiqh: mas'alas, rulings, evidence, madhhab, opinions | FR-071 | ADR-013, ADR-009 | T-094 | Designed (schema + fixture tests Built) |
| F.2 | Hadith: text, narrators, chains, grading, commentary | FR-071, FR-073 | ADR-013, ADR-009 | T-094, T-095 | Built (takhrij in footnotes) |
| F.3 | Tafseer: verses, explanations, interpretations | FR-071 | ADR-013 | T-094 | Designed (schema Built) |
| F.4 | Seerah: events, personalities, dates, locations | FR-071 | ADR-013 | T-094 | Designed (schema Built) |
| F.5 | Aqeedah: concepts, propositions, evidence | FR-071 | ADR-013, ADR-009 | T-094 | Designed (schema Built) |
| F.6 | Islamic history: events, personalities, chronology, places | FR-071 | ADR-013 | T-094 | Designed (schema Built) |
| F.7 | Biographies: scholars, teachers, students, birth/death | FR-071, FR-080 | ADR-013 | T-071, T-080–T-083 | Built |
| F.8 | Retain references to the original book and precise source location | FR-072, NFR-002 | ADR-003, ADR-007 | T-021, T-101 | Built |

### G. Knowledge graph and cross-book mapping

| # | Line | FR | ADR | Tickets | Status |
|---|---|---|---|---|---|
| G.1 | Entities and relationships among books, scholars, concepts, events, rulings, references | FR-080, FR-081 | ADR-018 | T-080–T-084 | Built |
| G.2 | Connect related knowledge units across different books | FR-082, FR-033 | ADR-018, ADR-005 | T-163, T-164 | Designed (graph-ready export Built) |
| G.3 | Support interconnected knowledge discovery | FR-083, FR-053 | ADR-005 | T-112, T-122 | Built (graph.html, search) / Designed (Neo4j) |

## §3 Required technical assessment

| # | Line | FR / NFR | ADR | Doc | Tickets | Status |
|---|---|---|---|---|---|---|
| 3.1 | System architecture: components, modular design, scalability | NFR-004, NFR-006 | ADR-001, ADR-002, ADR-004, ADR-005 | 02 | T-150 | Built (doc + diagram) |
| 3.2 | Data flow: input → processing → enrichment → validation → publishing | FR-001–FR-111 | ADR-004 | 02 data flow | T-151, T-140 | Built |
| 3.3 | Automation: Python scripts, orchestration, AI agents, task pipelines | FR-120, FR-122 | ADR-004, ADR-014 | 02, 06 | T-140–T-143, T-093 | Built |
| 3.4 | AI models: commercial APIs and open-weight per task | FR-121, NFR-007, NFR-008 | ADR-006 | 06 | T-090–T-092, T-152 | Built (gateway) / Designed (model matrix) |
| 3.5 | Arabic NLP: libraries, models, techniques | FR-050–FR-053 | ADR-012 | 06 | T-060–T-063 | Built |
| 3.6 | Knowledge infrastructure: relational, vector, graph, search engines | FR-110 | ADR-005 | 02, 03 | T-110–T-113, T-160–T-162 | Built (SQLite/JSON) / Designed (Postgres, Qdrant, Neo4j, OpenSearch) |
| 3.7 | Multi-model orchestration: comparison, validation, consensus, confidence, discrepancy detection | FR-090–FR-093 | ADR-007, ADR-008 | 06 | T-100–T-103 | Built |
| 3.8 | Human review mechanisms | FR-100–FR-102, NFR-011 | ADR-009, ADR-016 | 02, 03 | T-104, T-105, T-165 | Built (queue + HTML) / Designed (Argilla) |
| 3.9 | Model adaptation: fine-tuning, training data preparation, infrastructure | FR-123 | ADR-015 | 06, 08 | T-113, T-153, T-166, T-167 | Built (data export) / Designed (QLoRA) |
| 3.10 | Distinguish tasks best done by programming, NLP, LLM or agentic workflows | FR-122 | ADR-014 | 02 table, 06 | T-151, T-152 | Built (doc table) |

## §4 Expected data flow

| Step | Line | FR | Pipeline step (`pipeline/steps.py`) | Tickets | Status |
|---|---|---|---|---|---|
| 4.1 | Receive digitized text, PDF, identifiers | FR-001–FR-004, FR-010 | `ingest` → `adapt` → `integrity_register` | T-010–T-015, T-020 | Built |
| 4.2 | Analyse document structure | FR-040, FR-022 | `document_analysis`, `structure`, `origin` | T-030–T-034 | Built |
| 4.3 | Extract and enrich metadata | FR-020–FR-022 | `metadata` | T-040–T-042 | Built |
| 4.4 | Identify genre and related works | FR-070, FR-031, FR-032 | `genre`, `related_works` | T-095, T-053, T-084 | Built |
| 4.5 | Structural and semantic indexes | FR-040, FR-042 | `structure`, `search_index` | T-032, T-035, T-120, T-121 | Built / optional semantic |
| 4.6 | Identify and map annotations and references | FR-060–FR-063 | `annotations`, `citations` | T-050–T-054 | Built |
| 4.7 | Extract genre-specific knowledge units | FR-041, FR-071 | `units` | T-070–T-073, T-094 | Built |
| 4.8 | Identify entities and relationships | FR-080, FR-081, FR-052 | `entities`, `relations` | T-080–T-084 | Built |
| 4.9 | Validate with AI-based quality checks | FR-090–FR-093 | `validate` | T-100–T-103 | Built |
| 4.10 | Send uncertain or sensitive results to human review | FR-100–FR-102 | `review_queue` | T-103–T-105 | Built |
| 4.11 | Store approved info in the enrichment layer | FR-110 | `store` | T-110, T-111 | Built |
| 4.12 | Make enriched books and knowledge available for publishing and search | FR-111, FR-112, FR-053 | `export`, `search_index` | T-112, T-120–T-122, T-160 | Built (files) / Designed (API) |

## §5 Initial deliverables

| # | Deliverable / line | FR | Output | Tickets | Status |
|---|---|---|---|---|---|
| 5.0 | Preliminary architecture and capability assessment, not full development | Non-goals, release plan | 01 §10 | — | Built |
| 5.1 | System architecture diagram | FR-130 | `deliverables/diagrams/system-architecture.svg` | T-150 | Built |
| 5.2 | Automation and data-flow diagram (agents, scripts, DBs, human review) | FR-130 | `deliverables/diagrams/data-flow.svg` | T-151 | Built |
| 5.3 | Technology recommendations with purposes | FR-130 | Proposal §Technology | T-152 | Built |
| 5.4 | Arabic NLP and AI model strategy (optional) — commercial + open-weight | FR-130, FR-121 | Proposal §Models, 06 | T-152 | Built |
| 5.5 | Knowledge extraction approach: genre-specific, NER, source-location mapping | FR-130, FR-071, FR-072 | Proposal §Extraction, 06 | T-152 | Built |
| 5.6 | Model training approach: datasets, fine-tuning, LoRA/PEFT | FR-130, FR-123 | Proposal §Training, 06 | T-153, T-113 | Built (doc + data export) |
| 5.7 | MVP / PoC using sample PDF and JSON (optional) | FR-130 | `src/`, `output/`, MVP report | E00–E14, T-154 | Built |
| 5.7a | MVP: Metadata extraction | FR-020–FR-022 | `metadata.json` | T-040–T-042 | Built |
| 5.7b | MVP: Structural indexing | FR-040 | `structure.json` | T-031, T-032 | Built |
| 5.7c | MVP: Knowledge-unit extraction | FR-041, FR-071 | `knowledge_units.json` | T-070–T-073 | Built |
| 5.7d | MVP: Entity and relationship identification | FR-080, FR-081 | `entities.json`, `relationships.json` | T-080–T-084 | Built |
| 5.7e | MVP: Source-location mapping | FR-072, FR-112 | anchors in every file | T-021, T-101 | Built |
| 5.7f | MVP: Structured JSON output | FR-111 | `enrichment.json` + 16 files | T-112 | Built |
| 5.7g | A small prototype is sufficient | Release plan | — | — | Built |
| 5.8 | Implementation roadmap: phases, challenges, infrastructure, resources | FR-130 | `08-roadmap.md`, Proposal §Roadmap | T-154 | Built |

## §6 Technical considerations

| # | Consideration | NFR | ADR | Mechanism | Tickets | Status |
|---|---|---|---|---|---|---|
| 6.1 | Original book content remains untouched | NFR-001 | ADR-001, ADR-017 | Read-only store, before/after hash test, no write path | T-020, T-023 | Built |
| 6.2 | Enrichment stored separately, linked to original | NFR-002 | ADR-001, ADR-003 | Separate store; anchors `pub_ref + block_id + offsets + block_hash` | T-021, T-110 | Built |
| 6.3 | Every knowledge unit traceable to its source | NFR-002 | ADR-003, ADR-007 | Mandatory anchors with verbatim `quote`; evidence guard | T-021, T-101 | Built |
| 6.4 | Author statements distinguished from AI interpretations | NFR-003 | ADR-010 | `origin` (5 values) + `assertion` (stated/inferred) | T-033, T-034 | Built |
| 6.5 | Modular, repeatable, scalable processing | NFR-004–NFR-006 | ADR-002, ADR-004, ADR-011, ADR-013 | Plugins; deterministic IDs; cache; manifest; incremental reprocessing | T-011, T-022, T-141, T-142 | Built / Designed (scale) |
| 6.6 | AI outputs support confidence assessment and human approval | FR-092, FR-100 | ADR-008, ADR-009, ADR-016 | Confidence formula, sensitive rules, review queue, audit | T-102–T-105 | Built |

## §7 Reference materials

| # | Material | How it is used | Tickets | Status |
|---|---|---|---|---|
| 7.1 | Sample Islamic book PDF | Integrity hash; `scan_page` jump-to-source; printed indexes (pp. 73–80) as gold sample; visual checks | T-020, T-130, T-131 | Built |
| 7.2 | Digitized book JSON | Adapter input; all MVP steps; golden tests | T-010–T-015 | Built |
| 7.3 | Use materials to understand the input structure and assess feasibility | DECISIONS.md §7, `04-edge-cases.md`, MVP report | T-154 | Built |

## §8 Assessment focus

| # | Focus | Where it is demonstrated |
|---|---|---|
| 8.1 | Understanding of the requirements | 01 PRD, this matrix |
| 8.2 | System architecture and technical problem-solving | 02, ADR-001–ADR-018, 04 edge cases (real data findings) |
| 8.3 | Practical knowledge of AI automation and agentic workflows | ADR-004, ADR-014, the runnable MVP pipeline, 06 |
| 8.4 | Model selection and fine-tuning strategy | ADR-006, ADR-015, 06, T-152, T-153 |
| 8.5 | Technology choices and scalability | ADR-005, 02, 08 infrastructure, NFR-006 |
| 8.6 | Clarity and feasibility of the implementation approach | 08 roadmap, tickets with acceptance criteria, MVP results |
| 8.7 | Independent recommendations and alternatives welcomed | ADRs ("alternatives considered" in each), 08 risks |

---

## 9. Design pitfalls addressed

Common shortcuts in a first-pass design that this specification explicitly avoids.

| # | Pitfall | Addressed by |
|---|---|---|
| 1 | Book family / related works (Req B, step 4.4) almost absent | FR-030–FR-033, ADR-018, T-053, T-084, T-163 |
| 2 | Internal references ("ترجمة رقم (٣٣)") missing | FR-062, T-052 |
| 3 | Only Fiqh and Hadith schemas; Tafsir, Seerah, Aqeedah, History missing | FR-071, ADR-013, T-094 |
| 4 | Roadmap without durations, infrastructure, resources, challenges | `08-roadmap.md`, T-154 |
| 5 | Author vs AI distinction stated as principle with no mechanism | `origin` + `assertion`, ADR-010, T-033 |
| 6 | Repeatability: only model/prompt versions | ADR-011, deterministic IDs, cache, golden tests, manifest (T-141) |
| 7 | Adapter idea without registry, versioning, contract tests or unknown-field handling | FR-002–FR-004, ADR-002, T-011–T-014 |
| 8 | Revision change: the question is raised but not answered | FR-012, ADR-017 (block-hash re-validation, stale anchors, incremental reprocess), T-022 |
| 9 | "SHA256 integrity" assumes the source hash is reproducible (it is not) | ADR-017: own canonical + per-block hashes; Q-HASH open question |
| 10 | Assuming the JSON is OCR output | Source is Shamela; adapter keyed by `src-shamela` (DECISIONS §7) |
| 11 | Treating "72 vs 68 pages" as missing content (the 4 pages are non-content) | FR-022 explains missing pages 1, 2, 4, 18; issue severity `info` |
| 12 | Limiting traceability to block level (offsets are computable from block text) | ADR-003: offsets on original text; PDF linking is page-level |
| 13 | Presenting inferred facts (e.g. `daughter_of` Prophet) as stated | `assertion: inferred`, evidence = heading block (ADR-010) |
| 14 | Multiple entries per block, mid-sentence entries, sibling groups, "لأم ولد" vs "لأمه" | FR-041, FR-081, DECISIONS §11, `04-edge-cases.md` |
| 15 | Evidence check named but not specified | ADR-007 verbatim quote guard, FR-090 |
| 16 | Sensitive content handled only by "different thresholds" | ADR-009, always-review categories, FR-100 |
| 17 | A separate task queue (Celery + Redis) next to an orchestrator | ADR-004 (removed) |
| 18 | Turning every stage into an "agent" | ADR-014: four agents, the rest are workers |
| 19 | Nested footnote, continued footnotes, citation graph, printed index as gold | FR-060, FR-063, FR-031, T-130 |

## 10. Coverage summary

| Section | Lines | Mapped | Built (MVP) | Designed only |
|---|---|---|---|---|
| §1 | 7 | 7 | 6 | 1 (scale) |
| §2 A–G | 26 | 26 | 19 | 7 (cross-book, non-sample genres, hybrid vector) |
| §3 | 10 | 10 | 10 (docs) | parts in production |
| §4 | 12 | 12 | 12 | API part of 4.12 |
| §5 | 16 | 16 | 16 | — |
| §6 | 6 | 6 | 6 | scale part of 6.5 |
| §7 | 3 | 3 | 3 | — |
| §8 | 7 | 7 | 7 | — |
| **Total** | **87** | **87 (100%)** | — | — |

"Designed only" items are features that need more than one book, other genres or production infrastructure. Each one has a design (ADR + doc section) and a backlog ticket in E16.
