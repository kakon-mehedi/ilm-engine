# Decisions Register (single source of truth)

Every other document in `docs/` MUST use the names, paths, fields and values defined here.
If a document needs something not defined here, it adds it to this file first (and to the matching ADR).

- Scope source: the client's technical assignment brief (§1–§8; not included in this repository). [09-coverage-matrix.md](09-coverage-matrix.md) maps every line of it.
- Verified facts about the sample data: §7 below (every number was re-computed from the sample JSON).
- All documents are written so that a coding agent can execute the tickets without further context.

---

## 1. Scope of what gets built

| Track | What | Where |
|---|---|---|
| **Build (MVP)** | A runnable Python pipeline that processes the sample book end-to-end and writes the enrichment layer as JSON files (+ SQLite) | repository root (`src/`, `tests/`, `config/`) |
| **Design (production)** | Architecture for thousands of books: Prefect, PostgreSQL, Qdrant, Neo4j, OpenSearch, MinIO, Argilla, vLLM | documented only; backlog tickets in Epic E16 |
| **Deliverables** | Technical proposal + diagrams required by the assignment §5 | `deliverables/` |

## 2. Technology (MVP vs production)

| Concern | MVP | Production |
|---|---|---|
| Language / packaging | Python 3.12, `uv`, `pyproject.toml`, src layout | same |
| Models / validation | Pydantic v2 | same |
| CLI | `typer` → command `ilm-engine` | same + FastAPI service |
| Orchestration | In-process DAG runner (`pipeline/runner.py`), each step = idempotent function, cached by input hash | Prefect (steps map 1:1 to Prefect tasks) |
| LLM access | `llm/gateway.py` interface; providers `null` (default), `anthropic`, `litellm` | same via LiteLLM proxy |
| Arabic NLP | own normalizer (`nlp/normalize.py`, no deps) + optional CAMeL Tools | CAMeL Tools, Farasa |
| Embeddings | optional (E12): BGE-M3 via `sentence-transformers` if installed, else skipped | BGE-M3 on GPU |
| Storage | JSON files + SQLite `enrichment.db` | PostgreSQL (source of truth) → derived: Qdrant (vectors), Neo4j (graph), OpenSearch (search) |
| Original storage | `data/` treated read-only; copied to `store/originals/<pub_id>@r<rev>/` with hashes | MinIO/S3 with object lock |
| Review | `review_queue.json` + optional static HTML viewer | Argilla |
| Tests / lint | pytest, ruff, mypy (lenient) | same + CI |
| Observability | `run_manifest.json` + structured logs | OpenTelemetry + Grafana, Langfuse |

Not used: Celery + Redis (the orchestrator already queues and retries — ADR-004).

## 3. Repository layout (MVP)

```
ilm-engine/
  README.md
  pyproject.toml
  docs/                          # PRD, architecture, ADRs, contracts, tickets (this folder)
  data/                          # sample input (git-ignored; see data/README.md)
  config/
    default.yaml                 # thresholds, regexes, feature flags
    books/pub_01M0CJECV4ZHFTP02BJQ6D3STJ.yaml   # per-book overrides (origin ranges etc.)
  src/ilm_engine/
    __init__.py
    cli.py
    config.py
    ids.py                       # deterministic ID generation
    canonical/models.py          # CanonicalBook, Page, Block, Ref, Span
    adapters/
      base.py                    # SourceAdapter protocol
      registry.py                # (source_code, schema_version) -> adapter
      shamela_v3.py              # ShamelaV3Adapter
    integrity/
      hashing.py                 # canonical JSON hash, block hash
      store.py                   # read-only original store + verify
    nlp/
      normalize.py               # search normalization (never overwrites original)
      arabic_digits.py
      nasab.py                   # nasab chain parser
    processors/
      document_analysis.py       # quality checks, page gaps, stats
      structure.py               # section tree, TOC alignment
      origin.py                  # origin layer assignment
      metadata.py
      annotations.py             # refs, continued footnotes, nested footnotes
      citations.py               # external works cited + internal references
      genre.py
    extractors/
      units.py                   # knowledge units (biographical entries)
      entities.py
      relations.py               # sibling groups, parent/child, maternal/paternal
      related_works.py           # book family / related works
      llm_extract.py             # LLM structured extraction with evidence
      genres/                    # schema per genre: fiqh, hadith, tafsir, seerah, aqeedah, history, biography
    validation/
      evidence.py                # hallucination guard (quote must match source)
      rules.py
      consensus.py               # multi-model comparison
      confidence.py
      sensitivity.py
      review_queue.py
    storage/
      json_store.py
      sqlite_store.py
    search/
      lexical.py                 # normalized lexical index (MVP)
      semantic.py                # optional embeddings
    eval/
      gold.py                    # compare against printed index sample
    pipeline/
      steps.py
      runner.py
      manifest.py
    llm/
      gateway.py
      providers/null.py
      providers/fixture.py         # replays recorded responses (tests/CI)
      providers/anthropic.py
      providers/litellm.py
      cache.py
      prompts/                   # versioned prompt files: <task>.v<N>.md
  tests/
    golden/                      # adapter golden files
    ...
  eval/gold_index_sample.json    # hand-transcribed from PDF pp. 76–80
  output/                        # generated, git-ignored
  deliverables/
    Technical_Proposal.md
    diagrams/*.mmd, *.svg, *.png
```

## 4. Identifiers and anchors

- Book reference: `pub_ref = "<pub_id>@r<revision>"` → `pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6`.
- Block IDs: keep the source IDs (`b000135`). Never renumber.
- Our IDs are deterministic (same input → same ID): `<prefix>_<sha256(pub_ref + natural key)[:12]>`.
  Prefixes: `sec` section, `ku` knowledge unit, `ent` entity, `rel` relationship, `ann` annotation, `cit` citation, `wrk` work (cited/related), `iss` issue, `rev` review item, `run` run.
- **Anchor** (every fact/unit/annotation must carry ≥1):
  ```json
  {"pub_ref": "...@r6", "page": 25, "scan_page": 25, "block_id": "b000135",
   "start": 60, "end": 65, "quote": "أسلمت", "block_hash": "sha256:…"}
  ```
  Offsets = Python `str` indices (Unicode code points) on the **original, un-normalized** block text; `end` exclusive; `text[start:end] == quote` must hold.
- Offset rule check: entry 8 = `b000135`, length 102; `أسلمت` 60–65; `ولم يُروَ عنها شيءٌ` 78–97.

## 5. Integrity

- `block_hash = "sha256:" + sha256(block.text.encode("utf-8"))` (exact text, no normalization).
- `canonical_content_hash` = sha256 of canonical JSON of all blocks (`sort_keys=True, separators=(",",":"), ensure_ascii=False`).
- Source `content_sha256` is stored as `source_declared_hash` with `verified: false` (we could not reproduce its method — open question to the client).
- Invariant tests: hash of every file in `data/` identical before/after a run; every anchor's `block_hash` matches the current block; any mismatch → anchor `stale` + issue `anchor_stale`.

## 6. Origin layers (who said it)

| `origin` | Meaning | Sample book |
|---|---|---|
| `author_text` | Original author (al-Daraqutni) | page 20 from `b000098` → page 72 (excluding transmitter parts) |
| `transmission_isnad` | Transmitters / copyist (chain of narration, sama', copyist notes) | page 17 manuscript title page, page 19 isnad, end of page 72 |
| `editor_text` | Muhaqqiq's own text (introduction) | pages 3–16 |
| `editor_footnote` | Any `footnote` block | all 317 footnotes |
| `ai_generated` | Anything our system writes (summaries, classifications, inferred relations) | — |

Facts also carry `assertion`: `stated` (explicit in text) or `inferred` (derived, e.g. "daughter_of Prophet" from heading "أولاد رسول الله"). Inferred facts are always `ai_generated` and cite the evidence blocks.
Origin is assigned per section by rules (`processors/origin.py`) + per-book override YAML.

## 7. Verified sample-data facts (use these numbers)

594 blocks (text 260, footnote 317, heading 15, toc_heading 2) · 68 pages, `n` 3–72, missing 1, 2, 4, 18 (cover, publisher page, basmala, blank) · PDF 80 pages, `scan_page == PDF page`, PDF has no text layer · PDF pp. 73–80 = printed indexes: فهرس الأحاديث, فهرس الرواة المترجم لهم, الفهرس الإجمالي · source = Shamela (`src-shamela`), not OCR · 300 refs, all targets exist, 0 refs from footnotes · 16 `continues` footnotes · `b000215` (p.33, marker "أ") = nested footnote of `b000210` · TOC `source_page` = Shamela `source_ref.key`, offset to `n` varies (2→3→4) · 75 biographical entries numbered 1–75, no gap; #32 is mid-sentence in `b000294` ("وأختهم: ٣٢ - أروى"); 74 entry-level footnotes (#32 has none) · entry regex `(?<![٠-٩(/])([٠-٩]+) ?- ` on `author_text` blocks from page 21 · spans classes c2 (230, footnote markers), c5 (64, emphasis), c1 (8, Prophetic speech, inferred), c4 (2, editor bracket headings, inferred) · citations: الإصابة 144, أسد الغابة 67, السير 59, الطبقات الكبرى 45, الاستيعاب 31, التهذيب 32 … · quality record: claimed 72, held 68, short 5.6% > tolerance 5% yet `passed: true` · author death 385 AH stated in `b000049` (p.9).

## 8. Confidence & review

```
confidence = clamp01(base × evidence × schema × agreement × penalties)
base:      rule/structural 0.95 | llm 0.75
evidence:  exact quote match 1.0 | match after normalization 0.9 | no match 0 (reject)
schema:    valid 1.0 | valid after 1 repair retry 0.9 | invalid 0
agreement: two models agree ×1.2 | judge resolved 0.9 | single model 1.0 | disagree → issue model_disagreement
penalties: ambiguous entity ×0.8 | grammar mismatch ×0.7 | suspected OCR noise ×0.9
```
- Default auto-approve threshold `0.80` (config `review.threshold.default`); per-category overrides allowed (e.g. fiqh_ruling 0.95).
- **Sensitive → always review** regardless of score: `prophetic_attribution`, `hadith_grading`, `fiqh_ruling`, `aqeedah_proposition`, `narrator_disambiguation`.
- Review statuses: `auto_approved`, `pending_review`, `approved`, `rejected`, `edited`, `reprocess_requested`.

## 9. Issue codes (fixed list; add here first)

`unknown_schema_version`, `page_count_mismatch`, `missing_page`, `toc_without_block`, `toc_page_offset`, `heading_without_toc`, `unlinked_footnote`, `nested_footnote`, `continued_footnote_joined`, `broken_ref`, `numbering_gap`, `numbering_duplicate`, `entry_without_footnote`, `title_variant`, `metadata_conflict`, `evidence_not_found`, `schema_invalid`, `model_disagreement`, `ambiguous_entity`, `needs_llm`, `sensitive_content`, `unresolved_internal_ref`, `anchor_stale`, `source_hash_unverified`.

## 10. Output files (per run, `output/<pub_ref>/`)

`run_manifest.json`, `document_report.json`, `metadata.json`, `structure.json`, `origin_map.json`, `annotations.json`, `citations.json`, `related_works.json`, `knowledge_units.json`, `entities.json`, `relationships.json`, `search_index.json`, `validation_report.json`, `review_queue.json`, `enrichment.json` (consolidated), `enrichment.db` (SQLite), `eval_report.json` (written by `eval`), `graph.html` (optional).
Review loop: reviewer decisions are written to `review_decisions.json` and applied with `ilm-engine review apply`; approved/edited items are also exported to `training_examples.jsonl` (future fine-tuning data).
CLI commands: `ilm-engine run | verify | search | eval | review apply` (+ developer-only `ilm-engine dev regen-goldens`, run only on explicit human request).
`run` flags: `--input <json file | directory>` (a directory is scanned for one source JSON; the PDF is found via `_meta.scan.saved_file`), `--pdf <path>` (override), `--llm null|fixture|anthropic|litellm` (default `null`), `--out <dir>` (default `output/`).
LLM providers: `null` (default, no key, emits `needs_llm`), `fixture` (replays recorded responses from `tests/fixtures/llm/`; used in CI, no network), `anthropic`, `litellm`.
`run_manifest.json` holds: run_id, started/finished, code version (git sha), config hash, canonical schema version, adapter + version, model ids + prompt versions, input hashes, output hashes.

## 11. Genres and relation types

- Genres: `fiqh`, `hadith`, `tafsir`, `seerah`, `aqeedah`, `history`, `biography` (with sub-type `ansab` for this book). Sample book → primary `biography/ansab`, secondary `hadith` (takhrij in footnotes).
- Person relations: `child_of`, `parent_of`, `sibling_of` (attr `kind`: `full` | `paternal` | `maternal` | `unknown`), `spouse_of`, `mother_is`, `teacher_of`, `student_of`, `narrated_from`.
  Note: "لأم ولد" = mother was a slave-concubine (umm walad) — NOT maternal-sibling; "لأمه / لأم" with a named mother = maternal.
- Work relations: `sharh_of`, `hashiyah_of`, `mukhtasar_of`, `translation_of`, `edition_of`, `tahqiq_of`, `cites`, `same_topic_as`.

## 12. Agents (where "agentic" applies)

Only four LangGraph agents in production (MVP: plain functions behind the same interface): **Genre Router**, **Genre Extractor** (one per genre schema), **Related-Works / Citation Resolver** (tool: catalog search), **Discrepancy Resolver** (tools: re-read source, second model). Everything else is a deterministic worker.

## 12b. Pipeline step names (`pipeline/steps.py`, in execution order)

`ingest` → `adapt` → `integrity_register` → `document_analysis` → `structure` → `origin` → `metadata` → `genre` → `annotations` → `citations` → `related_works` → `units` → `entities` → `relations` → `search_index` → `validate` → `review_queue` → `store` → `export` → `integrity_verify` → `manifest`.
`ShamelaV3Adapter`: `source_code="src-shamela"`, `schema_version="3.0"`, `adapter_version="1.0.0"`.

## 12c. Additional conventions (from ADRs and data contracts)

- Module `src/ilm_engine/enrichment/models.py` holds all enrichment Pydantic models (Anchor, Issue, Section, KnowledgeUnit, …). `canonical/models.py` holds only canonical source models.
- Schema versions: `enrichment_schema_version = "1.0"`, `normalizer_version = "1.0.0"` (both recorded in `run_manifest.json`).
- CLI sub-commands (canonical spelling, reconciled with §10): `ilm-engine run`, `ilm-engine review html` (static `review.html`; also written automatically by `run`), `ilm-engine review apply <review_decisions.json>`, `ilm-engine rebuild-derived` (rebuild `search_index.json` / `graph.html` from `enrichment.db`), `ilm-engine schema export --out schemas/`.
- Extra outputs: `review.html` (from `review-html`), `training_examples.jsonl` (reviewed items for ADR-015; same file as §10), `schemas/*.json` (exported JSON Schemas, committed).
- Config file `config/works_aliases.yaml`: cited-title aliases → canonical Work (e.g. "الإصابة" → "الإصابة في تمييز الصحابة").
- Anchor `status`: `valid` | `stale` | `orphaned`; optional reserved `bbox`; `quote_truncated` for whole-block anchors (quote cut at 120 chars).
- Span meaning (inferred, configurable): `c2` footnote_marker, `c5` emphasis, `c1` prophetic_speech, `c4` editor_bracket_heading.
- Our `wrk_` IDs = 12 lowercase hex; source work IDs (`wrk_01M0…`, 26 uppercase Crockford) are stored as `source_work_id` — never confused.
- `InternalRef` IDs use prefix `ann`; sibling-group IDs use prefix `grp`.
- `RelationshipAttrs.mother_status`: `umm_walad` | `named` | `unknown` ("لأم ولد" → `umm_walad`, not `kind: maternal`).
- Production-only module folder `src/ilm_engine/agents/` (LangGraph agents of §12); in the MVP the four agents are plain functions in `processors/genre.py`, `extractors/llm_extract.py`, `extractors/related_works.py`, `validation/consensus.py`.
- Reviewer roles: `editor_reviewer`, `scholar_reviewer` (required for any sensitive category), `admin`.

## 13. Ticket conventions

- **Precedence:** `DECISIONS.md` > `03-data-contracts.md` (authoritative for every model/field name) > ADRs > tickets. If a ticket's field list differs from `03-data-contracts.md`, implement the contract and fix the ticket.

- Folder `docs/tickets/`, one file per ticket `T-<NNN>-<slug>.md`, epics `E00`–`E16`.
- Front matter: `id, title, epic, priority (P0/P1/P2), depends_on [ids], estimate (S/M/L), owner: agent, status: todo`.
- Sections: Context · Scope · Files · Implementation notes · Acceptance criteria (checkbox, testable) · Test commands · Out of scope.
- Definition of Done (all tickets): tests pass (`uv run pytest`), `ruff check` clean, no write to `data/`, docs updated, outputs deterministic (run twice → identical hashes).
