# ILM Engine

**Post-OCR knowledge enrichment for digitized Islamic books.**

ILM Engine takes a digitized book (structured JSON + page scans) and produces a separate, fully traceable **enrichment layer**: bibliographic metadata, a structural index, footnote and citation mapping, knowledge units, entities and relationships, related works, search and a knowledge graph. Every extracted item points back to the exact source location, and the original text is never modified.

> **Status:** MVP complete. All 72 MVP tickets are done ([docs/tickets/BOARD.md](docs/tickets/BOARD.md)); 10 production tickets are designed and backlogged. The main submission document is [deliverables/Technical_Proposal.md](deliverables/Technical_Proposal.md); the deliverables checklist is [deliverables/SUBMISSION_CHECKLIST.md](deliverables/SUBMISSION_CHECKLIST.md).

---

## Results on the sample book

*al-Ikhwa wa al-Akhawat* by al-Daraqutni (d. 385 AH), ed. al-Jawabira, Shamela export, 68 pages:

| | |
|---|---|
| Biographical entries (knowledge units) | **75 / 75**, numbered 1–75 without gaps |
| Footnote references resolved | **300 / 300**, plus 16 continued footnotes joined and 1 nested footnote |
| People / relationships | **111** / **173** (78 stated, 64 inferred and always reviewed, 31 mothers) |
| Citations | **674** citations of 99 works |
| Items for human review | **136** (15 sensitive, scholar only) |
| Evaluation vs the editor's printed index | precision **1.0**, recall **1.0** (75/75) |
| Run time, API keys needed | ≈4 s, none |
| Reruns | byte-identical outputs; original files unchanged |

## Principles

| Principle | How it is enforced |
|---|---|
| Original content is never modified | Inputs are copied to a read-only store; every file and block hash is re-checked at the end of each run |
| Every fact is traceable | Each record carries an anchor: `pub_ref + page + block_id + start/end + quote + block_hash`; a quote that is not the original text is rejected |
| The author's words are separate from AI output | Every record has an `origin` (`author_text`, `transmission_isnad`, `editor_text`, `editor_footnote`, `ai_generated`) and an `assertion` (`stated` / `inferred`) |
| No hallucinated facts | LLM output must quote the source verbatim; quotes that do not match the block are rejected |
| Humans approve what matters | Confidence scoring, multi-model consensus; sensitive categories (hadith grading, fiqh rulings, …) always go to scholar review |
| New formats do not break the system | Source adapters keyed by `(source_code, schema_version)` convert every input into one canonical schema; unknown versions fail closed |
| Repeatable | Deterministic IDs, cached LLM calls, versioned prompts, per-step cache and a run manifest |

## Quick start

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/). The sample book is confidential and not committed: put `demo_book_daraqutni.json` and `demo_book_daraqutni_v1.pdf` into `data/` first (see [data/README.md](data/README.md)).

```bash
uv sync
uv run ilm-engine run --input data          # narrates all 21 steps in 8 phases; writes output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6/
xdg-open "output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6/review.html"   # macOS: open …
```

More commands:

```bash
uv run ilm-engine eval                                   # precision/recall vs the printed index → eval_report.json, SUMMARY.md
uv run ilm-engine search "الدارقطني"                       # normalized search with page, block and origin
uv run ilm-engine verify output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6   # inputs, outputs and every anchor
uv run ilm-engine review apply decisions.json --book pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6
uv run ilm-engine rebuild-derived output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6   # search index + graph from enrichment.db
uv run ilm-engine run --list-steps                        # the 21 pipeline steps
uv run ilm-engine run --input data --quiet                # one status line per step instead of the narration
uv run pytest -q                                          # 680 tests
```

The pipeline runs without any API key (`--llm null`, the default): LLM-dependent work is flagged `needs_llm` for review. `--llm anthropic` (Claude via the `llm` extra, `uv sync --extra llm`) or `--llm litellm` enables model-based extraction; a verifier model from a different family can be configured in `config/default.yaml` for consensus.

## Outputs

Everything for one book is written to `output/<pub_ref>/`:

| File | Content |
|---|---|
| `enrichment.json` | Everything below in one validated document ([schema](docs/enrichment.schema.json)) |
| `enrichment.db` | SQLite copy of the enrichment (hashes only, no text) |
| `metadata.json`, `document_report.json` | Bibliographic record with provenance; counts, gaps and quality checks |
| `structure.json`, `origin_map.json` | Sections, TOC alignment, page index; who said each block |
| `annotations.json`, `citations.json`, `related_works.json` | Footnote links; cited works and internal references; book family |
| `knowledge_units.json`, `entities.json`, `relationships.json` | Entries with facts; people; family relations |
| `search_index.json`, `graph.html`, `graph.cypher` | Search index; knowledge graph (browser view and Neo4j import) |
| `validation_report.json`, `review_queue.json`, `review.html` | Checks and confidence per item; the review queue and its reviewer view |
| `run_manifest.json` | Run ID, code version, config hash, model and prompt versions, every input and output hash |
| `eval_report.json`, `SUMMARY.md` | Written by `ilm-engine eval` |

## Architecture at a glance

```mermaid
flowchart LR
    IN["Book JSON + PDF"] --> AD["Source adapter<br/>(per format/version)"]
    AD --> CB["Canonical book<br/>(read-only, hashed)"]
    CB --> P["Processing<br/>structure · origin · metadata<br/>annotations · citations"]
    P --> X["Extraction<br/>knowledge units · entities<br/>relationships (rules + LLM)"]
    X --> V["Validation<br/>evidence guard · consensus<br/>confidence · sensitivity"]
    V -->|confident| E["Enrichment layer"]
    V -->|uncertain / sensitive| R["Human review"]
    R --> E
    E --> S["Search · graph · publishing"]
```

Full diagrams: [system architecture](deliverables/diagrams/system-architecture.png), [data flow](deliverables/diagrams/data-flow.png), [agents](deliverables/diagrams/agent-workflow.png), [adapters](deliverables/diagrams/adapter-flow.png). Details: [docs/README.md](docs/README.md) and [docs/02-architecture.md](docs/02-architecture.md).

## Repository layout

```
ilm-engine/
├── src/ilm_engine/  Pipeline: adapters, integrity, nlp, processors, extractors, validation, storage, search, eval, llm, pipeline
├── config/          Thresholds, patterns, per-book overrides, cited-work aliases
├── tests/           Unit, golden, invariant and end-to-end tests
├── eval/            Gold sample transcribed from the printed index (evaluation only)
├── schemas/         Exported JSON Schemas of every contract model
├── deliverables/    Technical proposal, diagrams, submission checklist
├── docs/            Requirements, architecture, ADRs, data contracts, tickets
└── data/            Sample input (git-ignored, see data/README.md)
```

## Known limitations

- LLM extraction, consensus and the judge are implemented and tested with scripted model responses; the figures above are from a run without a model (rule-based facts only).
- Parents named in sibling closures are new people, not yet linked to the same person's own entry (e.g. "عمر" and entry #54).
- Page- and name-based backward references ("تقدمت ترجمته (ص: ٢٨)") are kept and sent to review rather than resolved.
- Biography is fully implemented and hadith takhrij/grading detection works; the other five genre plugins have schemas only.
- Production infrastructure (Prefect, PostgreSQL, Qdrant, Neo4j, OpenSearch, Argilla, FastAPI, vLLM) is designed and backlogged (tickets T-160–T-169), not built.

## Open questions for the client

How `content_sha256` is computed (it cannot be reproduced, so integrity relies on our own hashes); whether block IDs are stable across revisions; a sample of the OCR team's format; whether some books must not be sent to external LLM APIs; whether an authority list of narrators exists; real volumes and reviewer capacity. See [Technical_Proposal.md](deliverables/Technical_Proposal.md#assumptions-and-open-questions).

## Documentation

| Document | Purpose |
|---|---|
| [deliverables/Technical_Proposal.md](deliverables/Technical_Proposal.md) | The submission: architecture, models, extraction, training, MVP results, roadmap |
| [docs/README.md](docs/README.md) | Visual walkthrough of the pipeline, from one JSON block to the final enrichment records |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Single source of truth for names, paths, IDs, thresholds and issue codes |
| [docs/01-PRD.md](docs/01-PRD.md) | Product requirements (functional and non-functional) |
| [docs/02-architecture.md](docs/02-architecture.md) | Components, layers, storage, deployment |
| [docs/03-data-contracts.md](docs/03-data-contracts.md) | Canonical and enrichment schemas |
| [docs/04-edge-cases.md](docs/04-edge-cases.md) | Edge-case catalogue with detection and handling |
| [docs/06-ai-strategy.md](docs/06-ai-strategy.md) | Model selection, genre schemas, confidence, fine-tuning |
| [docs/07-test-plan.md](docs/07-test-plan.md) | Test strategy and acceptance tests |
| [docs/08-roadmap.md](docs/08-roadmap.md) | Phases, challenges, infrastructure, resources |
| [docs/09-coverage-matrix.md](docs/09-coverage-matrix.md) | Traceability from every requirement to design and tickets |
| [docs/ADAPTERS.md](docs/ADAPTERS.md) | How to add a source format |
| [docs/adr/](docs/adr/README.md) | Architecture decision records |
| [docs/tickets/](docs/tickets/BOARD.md) | Implementation tickets, dependency graph and execution waves |
