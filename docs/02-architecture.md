# 02 — Architecture

Status: Accepted (v1.0). Names, paths, fields and thresholds follow [DECISIONS.md](DECISIONS.md). Decisions with alternatives are recorded in [adr/](adr/).

---

## 1. Architectural principles

| # | Principle | Consequence |
|---|---|---|
| P1 | **Original content is immutable** | `data/` and the original store are read-only; enrichment never copies-and-edits text; integrity is checked by hashes every run |
| P2 | **Enrichment is a separate, linked layer** | Every record references the source by an **anchor** (`pub_ref, page, block_id, start, end, quote, block_hash`) |
| P3 | **Traceability is mandatory** | A fact without a verifiable anchor is rejected (`evidence_not_found`) |
| P4 | **Provenance of voice** | Every unit/fact carries `origin` (`author_text`, `transmission_isnad`, `editor_text`, `editor_footnote`, `ai_generated`) and `assertion` (`stated` / `inferred`) |
| P5 | **Source-agnostic core** | Only adapters know source formats; everything downstream consumes `CanonicalBook` |
| P6 | **Fail closed** | Unknown schema versions, invalid schemas or hash mismatches stop the step and raise an issue; nothing is guessed |
| P7 | **Deterministic first, AI second** | Use code where the data already has structure; NLP for linguistics; LLM only where meaning is required; agents only where multi-step decisions/tools are required |
| P8 | **Repeatable** | Deterministic IDs, pinned model + prompt versions, temperature 0, response cache, run manifest; same input → same output hashes |
| P9 | **Human authority on sensitive content** | Sensitive categories always go to review regardless of confidence |
| P10 | **Modular & replaceable** | Each layer is a step with a typed input/output contract; any layer, model or store can be swapped |

---

## 2. Context diagram

```mermaid
flowchart LR
    SRC["Source archives<br/>(Shamela, OCR team, future)"] -->|"JSON + PDF + identifiers"| SYS
    SYS["Kitab Enrich<br/>enrichment platform"]
    LLM["LLM providers<br/>(Anthropic, other via LiteLLM,<br/>self-hosted vLLM)"] <-->|"structured extraction<br/>verification"| SYS
    AUTH["Authority data<br/>(narrator DBs, catalogues)"] -->|"entity / work linking"| SYS
    REV["Reviewers<br/>(scholars, editors)"] <-->|"approve / edit / reject"| SYS
    SYS -->|"approved enrichment"| PUB["Digital library<br/>reader · search · discovery"]
    OPS["Operators"] -->|"runs, config, monitoring"| SYS
```

---

## 3. Container / component view

### 3.1 Production

```mermaid
flowchart TB
    subgraph Ingest["Ingestion"]
        GW["Input Gateway<br/>(FastAPI)"]
        REG["Adapter Registry"]
        OBJ[("MinIO / S3<br/>object lock<br/>originals")]
    end

    subgraph Orch["Orchestration"]
        PF["Prefect server"]
        WK["Worker pool<br/>(CPU, k8s)"]
    end

    subgraph Proc["Processing services (Python packages run by workers)"]
        DA["document_analysis"]
        ST["structure + origin"]
        MD["metadata + genre"]
        AN["annotations + citations"]
        EX["extractors<br/>(units, entities, relations, related_works)"]
        NLP["nlp<br/>(normalize, nasab, CAMeL)"]
    end

    subgraph AI["AI layer"]
        LG["LLM Gateway<br/>(LiteLLM)"]
        PR["Prompt & schema registry"]
        AG["LangGraph agents<br/>(4)"]
        VLLM["vLLM GPU pool<br/>(open-weight + LoRA)"]
        CACHE[("Response cache")]
    end

    subgraph Val["Validation"]
        EVd["evidence guard"]
        CON["consensus + judge"]
        CONF["confidence + sensitivity"]
    end

    subgraph Rev["Human review"]
        ARG["Argilla"]
    end

    subgraph Store["Knowledge store"]
        PG[("PostgreSQL<br/>source of truth")]
        QD[("Qdrant<br/>vectors")]
        NEO[("Neo4j<br/>graph")]
        OS[("OpenSearch<br/>Arabic search")]
    end

    subgraph Serve["Serving"]
        API["Library API (FastAPI)"]
    end

    subgraph X["Cross-cutting"]
        OT["OpenTelemetry + Grafana"]
        LF["Langfuse (LLM traces, cost)"]
        AUD["Audit log"]
    end

    GW --> REG --> OBJ
    GW --> PF --> WK
    WK --> DA & ST & MD & AN & EX & NLP
    EX --> AG --> LG
    MD --> LG
    LG --> VLLM
    LG --> CACHE
    PR --> LG
    EX --> EVd --> CON --> CONF
    CONF -->|"pending_review"| ARG --> PG
    CONF -->|"auto_approved"| PG
    PG -->|"projection jobs"| QD & NEO & OS
    PG & QD & NEO & OS --> API
```

### 3.2 MVP (single process, no infrastructure)

```mermaid
flowchart LR
    CLI["ilm-engine CLI<br/>(typer)"] --> RUN["pipeline/runner.py<br/>in-process DAG"]
    RUN --> ADP["adapters/registry.py<br/>→ shamela_v3.py"]
    ADP --> CAN["canonical/models.py<br/>CanonicalBook"]
    RUN --> INT["integrity/"]
    RUN --> PRC["processors/*"]
    RUN --> EXT["extractors/*"]
    EXT --> GWY["llm/gateway.py<br/>null | anthropic | litellm"]
    GWY --> CCH[("llm/cache.py<br/>cache/&lt;sha256&gt;.json")]
    RUN --> VAL["validation/*"]
    VAL --> JS[("storage/json_store.py<br/>output/&lt;pub_ref&gt;/*.json")]
    VAL --> SQ[("storage/sqlite_store.py<br/>enrichment.db")]
    RUN --> MAN["pipeline/manifest.py<br/>run_manifest.json"]
```

The MVP and production share the same package; production swaps the runner for Prefect and the stores for Postgres + projections (ADR-004, ADR-006).

---

## 4. Layer-by-layer specification

All steps are pure functions of their inputs + config + model responses, registered in `pipeline/steps.py`:

```python
class Step(Protocol):
    name: str
    version: str                     # bump when logic changes
    depends_on: tuple[str, ...]
    def run(self, ctx: RunContext) -> StepResult: ...

@dataclass
class StepResult:
    outputs: dict[str, Any]          # keyed by output file name
    issues: list[Issue]
```

`RunContext` provides: `book: CanonicalBook`, `config`, `llm: LLMGateway`, `results: dict[str, StepResult]` of dependencies, `ids: IdFactory`, `logger`.

| # | Layer / module | Responsibility | Inputs | Outputs | Method | Failure modes → handling |
|---|---|---|---|---|---|---|
| L1 | `adapters/*` | Parse source JSON into `CanonicalBook` | raw JSON | `CanonicalBook` | 🟦 | unknown `(source_code, schema_version)` → `unknown_schema_version`, stop; missing required field → `schema_invalid`, stop |
| L2 | `integrity/*` | Copy originals read-only, compute `block_hash`, `canonical_content_hash`; record `source_declared_hash` | raw files, `CanonicalBook` | hashes → `run_manifest.json` | 🟦 | hash mismatch with previous run of same revision → stop; source hash not reproducible → `source_hash_unverified` (warn) |
| L3 | `processors/document_analysis.py` | Page gaps, counts, quality reconciliation, empty/duplicate blocks | `CanonicalBook`, source quality record | `document_report.json` | 🟦 | `missing_page`, `page_count_mismatch` (classified: non-content vs content) |
| L4 | `processors/structure.py` | Section tree from `heading`/`toc_heading`; align TOC (`source_page` = Shamela key) | blocks, TOC | `structure.json` | 🟦 (+🟧 for unmarked sources) | `toc_without_block`, `heading_without_toc`, `toc_page_offset` |
| L5 | `processors/origin.py` | Assign `origin` per block by section rules + per-book override YAML | structure, config | `origin_map.json` | 🟦 | block with no rule → `editor_text` default + `needs_llm` |
| L6 | `processors/metadata.py` | Bibliographic record from card + preface evidence; conflicts | metadata card, preface blocks | `metadata.json` | 🟦 + 🟧 | `metadata_conflict`, `title_variant` |
| L7 | `processors/genre.py` | Primary/secondary genre; selects extractor schema | category, sampled content | `metadata.json#genre` | 🟦 + 🟧 (Genre Router) | low confidence → review |
| L8 | `processors/annotations.py` | Resolve `refs`; join `continues` footnotes; nested footnotes by marker | blocks | `annotations.json` | 🟦 | `broken_ref`, `unlinked_footnote`, `nested_footnote`, `continued_footnote_joined` |
| L9 | `processors/citations.py` | External works cited (title + vol/page) and internal references ("ترجمة رقم (٣٣)", "كما سيأتي") | footnotes, text | `citations.json` | 🟦 + 🟩 | `unresolved_internal_ref` |
| L10 | `extractors/units.py` (+ `genres/*`) | Knowledge units per genre schema; for this book 75 biographical entries | `author_text` blocks, annotations | `knowledge_units.json` | 🟦 + 🟧 (Genre Extractor) | `numbering_gap`, `numbering_duplicate`, `entry_without_footnote` |
| L11 | `extractors/entities.py`, `nlp/nasab.py` | Person entities, nasab chains, aliases, linking | units, footnotes | `entities.json` | 🟩 + 🟧 | `ambiguous_entity` |
| L12 | `extractors/relations.py` | Sibling groups (closing phrases "ابنا…", "بنو…"), parent/child, maternal/paternal, umm walad | units, entities | `relationships.json` | 🟦 + 🟧 | grammar mismatch penalty; `needs_llm` without provider |
| L13 | `extractors/related_works.py` | Book family / related works (`cites`, `same_topic_as`, `sharh_of`…) | citations, preface | `related_works.json` | 🟦 + 🟧 (Citation Resolver) | unresolved title → review |
| L14 | `search/lexical.py`, `search/semantic.py` | Normalized lexical index; optional embeddings | blocks, units | `search_index.json` | 🟩 | embeddings unavailable → skipped, recorded in manifest |
| L15 | `validation/*` | Evidence guard, rules, consensus, confidence, sensitivity | all extracted records | `validation_report.json` | 🟦 + 🟧 (Discrepancy Resolver) | `evidence_not_found` → reject; `model_disagreement` → review |
| L16 | `validation/review_queue.py` | Build review items with context + PDF page | validated records | `review_queue.json` | 🟦 → 🟥 | — |
| L17 | `storage/*` | Persist enrichment; consolidated export | everything | `enrichment.json`, `enrichment.db` | 🟦 | write failure → run marked failed, no partial publish |

---

## 5. Adapter subsystem

```mermaid
classDiagram
    class SourceAdapter {
        <<Protocol>>
        +source_code: str
        +schema_versions: tuple~str~
        +adapter_version: str
        +detect(raw: dict) bool
        +to_canonical(raw: dict) CanonicalBook
    }
    class AdapterRegistry {
        +register(adapter)
        +resolve(source_code, schema_version) SourceAdapter
    }
    class ShamelaV3Adapter {
        source_code = "src-shamela"
        schema_versions = ("3.0",)
        adapter_version = "1.0.0"
    }
    class CanonicalBook {
        canonical_schema_version = "1.0"
        book_ref
        source
        metadata_raw
        pages[]
        blocks[]
        raw_extras
    }
    SourceAdapter <|.. ShamelaV3Adapter
    AdapterRegistry o-- SourceAdapter
    ShamelaV3Adapter ..> CanonicalBook : produces
```

- **Resolution key:** `(source_code, schema_version)`, read from `pub.source_code` and `revision.content.schema_version` (Shamela v3). No match → `unknown_schema_version` and stop (fail-closed).
- **Field mapping (Shamela v3 → canonical):** `b → id`, `kind → kind`, `text → text`, `marker`, `continues`, `spans`, `refs[{start,end,to}]`; page `n → page`, `scan_page`, `source_ref.key → source_key`, `source_ref.url → url`, `volume`; `order` = global position.
- **`raw_extras`:** any source field the adapter does not map is preserved verbatim under `raw_extras` (book, page or block level). Nothing is dropped silently.
- **Golden tests:** `tests/golden/<adapter>/<case>.input.json` → `<case>.canonical.json`. Every adapter must pass its golden cases; changes to the canonical output require updating the golden file in the same PR.
- **Versioning:** `canonical_schema_version` (`1.0`) changes only via ADR. Adapters have their own semver. Both are written into `run_manifest.json`.
- **Adding a source:** new file in `adapters/`, one `registry.register(...)` line, golden cases. No downstream change.

---

## 6. Integrity subsystem

```mermaid
sequenceDiagram
    participant R as runner
    participant I as integrity/store.py
    participant H as integrity/hashing.py
    participant M as manifest
    R->>I: register_originals(data/*.json, *.pdf)
    I->>H: file_sha256(each)
    I-->>R: originals copied to store/originals/<pub_ref>/ (chmod 0444)
    R->>H: block_hash(block) for all blocks
    R->>H: canonical_content_hash(book)
    H-->>M: input hashes, source_declared_hash (verified=false)
    Note over R: ... pipeline runs ...
    R->>I: verify_unchanged()
    I->>H: re-hash data/ files
    alt any differs
        I-->>R: FAIL run (originals modified)
    end
    R->>H: verify_anchors(all records)
    alt block_hash mismatch or text[start:end] != quote
        H-->>R: anchor_stale / evidence_not_found
    end
```

- `block_hash = "sha256:" + sha256(text.encode("utf-8"))`, exact text, no normalization.
- **Revision change (r6 → r7):** compare block hashes per `block_id`. Unchanged → records carried over (re-anchored to new `pub_ref`); changed/removed → `anchor_stale`, record re-processed and sent to review; new blocks → processed.
- Pipeline code has no write path to `data/` or `store/originals/` (enforced by a test that hashes before/after).

---

## 7. LLM gateway

```python
class LLMGateway(Protocol):
    def extract(self, task: str, prompt_version: str, input: dict,
                schema: type[BaseModel], model: str | None = None) -> LLMResult: ...

@dataclass
class LLMResult:
    data: BaseModel | None      # validated against schema
    model: str                  # e.g. "claude-sonnet-5-5"
    prompt_version: str         # e.g. "relations.v1"
    cached: bool
    repaired: bool              # needed one schema-repair retry
    raw: str
```

- Providers: `null` (default; returns `None` → caller emits `needs_llm`), `anthropic`, `litellm` (any second provider / self-hosted vLLM).
- Prompts are versioned files `llm/prompts/<task>.v<N>.md`; the version is part of the cache key and the manifest.
- Determinism: temperature 0; cache key = `sha256(provider + model + prompt_version + canonical_json(input))`; cache stored under `cache/`.
- Every LLM output must include verbatim `quote` evidence; the evidence guard computes offsets and rejects non-matching quotes.
- Routing: Haiku-class for cheap classification, Sonnet-class for extraction, Opus-class or a different family as judge (see `06-ai-strategy.md`).

---

## 8. Agent workflow (the only four agents)

```mermaid
stateDiagram-v2
    [*] --> GenreRouter
    GenreRouter --> GenreExtractor: genre + schema chosen
    GenreRouter --> HumanReview: low confidence genre
    GenreExtractor --> EvidenceGuard
    EvidenceGuard --> Consensus: quotes verified
    EvidenceGuard --> Rejected: quote not found
    Consensus --> CitationResolver: agreed
    Consensus --> DiscrepancyResolver: disagreement
    DiscrepancyResolver --> CitationResolver: resolved (judge 0.9)
    DiscrepancyResolver --> HumanReview: unresolved
    CitationResolver --> Confidence
    Confidence --> Approved: >= threshold and not sensitive
    Confidence --> HumanReview: below threshold or sensitive
    HumanReview --> Approved
    HumanReview --> Rejected
    Approved --> [*]
    Rejected --> [*]
```

| Agent | Decides | Tools |
|---|---|---|
| **Genre Router** | which genre schema(s) and extractor to run | metadata reader, block sampler |
| **Genre Extractor** | knowledge units per genre schema | block reader, footnote reader, schema validator |
| **Related-Works / Citation Resolver** | which catalogued work a citation or mention refers to | catalog search, normalized title matcher |
| **Discrepancy Resolver** | how to settle model disagreement or metadata conflicts | re-read source, call second model, open issue |

In the MVP these are plain functions behind the same interface; production implements them as LangGraph graphs (ADR-005). Everything else is a deterministic worker.

---

## 9. Storage design

### 9.1 Production (PostgreSQL = source of truth)

```mermaid
erDiagram
    BOOK ||--o{ REVISION : has
    REVISION ||--o{ SOURCE_BLOCK : contains
    REVISION ||--o{ RUN : processed_by
    RUN ||--o{ KNOWLEDGE_UNIT : produced
    KNOWLEDGE_UNIT ||--o{ FACT : asserts
    FACT ||--o{ ANCHOR : evidenced_by
    ANCHOR }o--|| SOURCE_BLOCK : points_to
    ENTITY ||--o{ ENTITY_ALIAS : known_as
    ENTITY ||--o{ RELATIONSHIP : subject
    RELATIONSHIP ||--o{ ANCHOR : evidenced_by
    ANNOTATION }o--|| SOURCE_BLOCK : from
    CITATION }o--|| WORK : cites
    WORK ||--o{ WORK_RELATION : related
    ISSUE }o--|| RUN : raised_in
    REVIEW_ITEM }o--|| ISSUE : about
    REVIEW_ITEM ||--o{ REVIEW_ACTION : history

    BOOK { text pub_id PK  text work_id  text canonical_title }
    REVISION { text pub_ref PK  int revision  text canonical_content_hash  text source_declared_hash  text canonical_schema_version }
    SOURCE_BLOCK { text pub_ref FK  text block_id  int page  int scan_page  text kind  text block_hash  text origin }
    RUN { text run_id PK  text code_version  text config_hash  jsonb models  jsonb prompt_versions }
    KNOWLEDGE_UNIT { text ku_id PK  text type  text genre  text origin  jsonb data  float confidence  text review_status }
    FACT { text fact_id PK  text predicate  jsonb value  text assertion  text origin }
    ANCHOR { text anchor_id PK  text block_id  int start  int end  text quote  text block_hash  bool stale }
    ENTITY { text ent_id PK  text type  text canonical_name  jsonb nasab }
    RELATIONSHIP { text rel_id PK  text type  text kind  text source_ent  text target_ent  float confidence }
    WORK { text wrk_id PK  text title  text normalized_title }
    ISSUE { text iss_id PK  text code  text severity  jsonb target }
    REVIEW_ITEM { text rev_id PK  text status  text category  bool sensitive }
```

Original text is **not** stored in Postgres (it lives in the object store); `SOURCE_BLOCK` holds identity, position and hash only.

**Derived, rebuildable stores** (projection jobs from Postgres; can be dropped and rebuilt any time):

| Store | Content | Rebuilt from |
|---|---|---|
| Qdrant | embeddings of blocks and units (BGE-M3) | `SOURCE_BLOCK` + original text, `KNOWLEDGE_UNIT` |
| Neo4j | entities, works, relationships, citations | `ENTITY`, `RELATIONSHIP`, `WORK`, `CITATION` |
| OpenSearch | original + normalized text, Arabic analyzer, hybrid BM25 + vector | object store text + Postgres metadata |

### 9.2 MVP (SQLite `enrichment.db`)

Tables mirror the above with `TEXT` JSON columns: `books, revisions, source_blocks, runs, knowledge_units, facts, anchors, entities, entity_aliases, relationships, annotations, citations, works, work_relations, issues, review_items`. The JSON files in `output/<pub_ref>/` are the primary MVP output; SQLite is written from the same objects (`storage/sqlite_store.py`).

---

## 10. Data flow: assignment §4 (12 steps) → pipeline steps

```mermaid
flowchart TD
    S1["1. Receive text, PDF, identifiers<br/>ingest · adapt · integrity"]:::code
    S2["2. Analyse structure<br/>document_analysis · structure · origin"]:::code
    S3["3. Extract & enrich metadata<br/>metadata"]:::llm
    S4["4. Genre & related works<br/>genre · related_works"]:::llm
    S5["5. Structural & semantic indexes<br/>structure · search_index"]:::nlp
    S6["6. Annotations & references<br/>annotations · citations"]:::code
    S7["7. Genre-specific knowledge units<br/>units"]:::llm
    S8["8. Entities & relationships<br/>entities · relations"]:::nlp
    S9["9. AI quality checks<br/>evidence · consensus · confidence"]:::llm
    S10["10. Uncertain / sensitive → human<br/>review_queue"]:::human
    S11["11. Store approved enrichment<br/>store"]:::code
    S12["12. Publish & search<br/>export · projections · API"]:::code

    S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> S8 --> S9 --> S10 --> S11 --> S12
    S9 -->|auto_approved| S11

    classDef code fill:#dbeafe,stroke:#1d4ed8,color:#000
    classDef nlp fill:#dcfce7,stroke:#15803d,color:#000
    classDef llm fill:#ffedd5,stroke:#c2410c,color:#000
    classDef human fill:#fee2e2,stroke:#b91c1c,color:#000
```

| Assignment step | `pipeline/steps.py` step names | Output file(s) |
|---|---|---|
| 1 Receive | `ingest`, `adapt`, `integrity_register` | `run_manifest.json` |
| 2 Structure | `document_analysis`, `structure`, `origin` | `document_report.json`, `structure.json`, `origin_map.json` |
| 3 Metadata | `metadata` | `metadata.json` |
| 4 Genre + related works | `genre`, `related_works` | `metadata.json#genre`, `related_works.json` |
| 5 Indexes | `structure` (structural), `search_index` (semantic/lexical) | `structure.json`, `search_index.json` |
| 6 Annotations + references | `annotations`, `citations` | `annotations.json`, `citations.json` |
| 7 Knowledge units | `units` | `knowledge_units.json` |
| 8 Entities + relationships | `entities`, `relations` | `entities.json`, `relationships.json` |
| 9 AI quality checks | `validate` | `validation_report.json` |
| 10 Human review | `review_queue` | `review_queue.json` |
| 11 Store | `store` | `enrichment.db` |
| 12 Publish + search | `export` (MVP), projection jobs + API (production) | `enrichment.json`, `graph.html` |

Final step always: `integrity_verify` (originals unchanged, anchors valid) and `manifest`.

---

## 11. Deployment view (production)

```mermaid
flowchart TB
    subgraph K8s["Kubernetes cluster"]
        API["library-api<br/>(FastAPI, HPA)"]
        GWY["input-gateway"]
        PFS["prefect-server"]
        CPU["cpu-workers<br/>(processors, NLP)<br/>autoscale on queue depth"]
        LLMW["llm-workers<br/>(gateway clients, agents)"]
        PROJ["projection-jobs<br/>(Qdrant, Neo4j, OpenSearch)"]
        ARG["argilla"]
        LIT["litellm-proxy"]
    end
    subgraph GPU["GPU node pool"]
        VLLM["vLLM<br/>base model + multi-LoRA"]
        EMB["embedding server<br/>BGE-M3"]
    end
    subgraph Data["Managed data services"]
        PG[("PostgreSQL<br/>primary + replica")]
        S3[("MinIO / S3<br/>object lock")]
        QD[("Qdrant")]
        NEO[("Neo4j")]
        OS[("OpenSearch")]
    end
    EXT["Commercial LLM APIs"]

    GWY --> S3
    GWY --> PFS --> CPU & LLMW
    LLMW --> LIT --> VLLM & EXT
    CPU --> EMB
    CPU & LLMW --> PG
    PG --> PROJ --> QD & NEO & OS
    API --> PG & QD & NEO & OS
    ARG --> PG
```

---

## 12. Scalability & performance

| Concern | Approach |
|---|---|
| Throughput | Book-level parallelism across workers; block-batch parallelism inside LLM steps; queue-depth autoscaling |
| LLM cost | Deterministic steps first (most of this book needs no LLM); route by difficulty (small → large model); batch APIs for bulk runs; response cache; fine-tuned open-weight models for high-volume tasks |
| Re-processing | Incremental: only steps whose `version`, config or input hash changed re-run; on new revision only changed blocks re-process |
| Storage growth | Postgres partitioned by `pub_ref` / genre; derived stores rebuilt asynchronously |
| Latency (serving) | Reads from OpenSearch/Qdrant/Neo4j projections; Postgres for detail |
| Back-pressure | Prefect concurrency limits per provider (rate limits), per GPU pool |

---

## 13. Extensibility points

| To add | Change only |
|---|---|
| New source / JSON format | new adapter + registry line + golden tests |
| New genre | `extractors/genres/<genre>.py` schema + prompt file + Genre Router label |
| New model / provider | gateway provider config; prompts unchanged; eval run before switching |
| New language | normalizer profile in `nlp/`, analyzer in OpenSearch, prompts per language |
| New relation / work-relation type | DECISIONS §11 + contract + ADR |
| New issue code | DECISIONS §9 first |

---

## 14. Security & privacy

- Originals in object storage with object lock; workers have read-only credentials to originals and write-only to enrichment tables.
- Secrets (API keys) via environment / secret manager, never in config files or manifests.
- Data sent to external LLMs is limited to the blocks needed for a task; a per-source policy flag can force self-hosted models only (open question to client: privacy restrictions).
- Reviewer actions are authenticated and written to an append-only audit log (`REVIEW_ACTION`).
- AI-generated interpretations are never published as scholarly statements: `origin = ai_generated` is visible in every API response.
