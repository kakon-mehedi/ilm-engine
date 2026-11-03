# ILM Engine

**Post-OCR knowledge enrichment for digitized Islamic books.**

ILM Engine takes a digitized book (structured JSON + page scans) and produces a separate, fully traceable **enrichment layer**: bibliographic metadata, a structural index, footnote and citation mapping, knowledge units, entities and relationships. Every extracted item points back to the exact source location, and the original text is never modified.

> **Status:** design and specification complete; the MVP is implemented ticket by ticket (see [docs/tickets/BOARD.md](docs/tickets/BOARD.md)).

---

## Principles

| Principle | How it is enforced |
|---|---|
| Original content is never modified | Inputs are read-only; per-block SHA-256 hashes are verified after every run |
| Every fact is traceable | Each record carries an anchor: `pub_ref + page + block_id + start/end + quote + block_hash` |
| The author's words are separate from AI output | Every record has an `origin` (`author_text`, `transmission_isnad`, `editor_text`, `editor_footnote`, `ai_generated`) and an `assertion` (`stated` / `inferred`) |
| No hallucinated facts | LLM output must quote the source verbatim; quotes that do not match the block are rejected |
| Humans approve what matters | Confidence scoring, multi-model consensus, and sensitive categories (e.g. hadith grading, fiqh rulings) are always routed to scholar review |
| New formats do not break the system | Source adapters keyed by `(source_code, schema_version)` convert every input into one canonical schema; unknown versions fail closed |
| Repeatable | Deterministic IDs, cached LLM calls at temperature 0, versioned prompts, and a run manifest |

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

Details: [docs/README.md](docs/README.md) (how the system works) and [docs/02-architecture.md](docs/02-architecture.md).

## Repository layout

```
ilm-engine/
├── docs/            Requirements, architecture, ADRs, data contracts, tickets
├── data/            Sample input (git-ignored, see data/README.md)
├── src/ilm_engine/  Pipeline source code
├── tests/           Unit, golden, invariant and end-to-end tests
├── config/          Thresholds, rules and per-book overrides
└── deliverables/    Technical proposal and exported diagrams
```

## Quick start

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/). Place the sample files in `data/` first (see [data/README.md](data/README.md)). The commands below become available as the E00–E14 tickets land.

```bash
uv sync
uv run ilm-engine run --input data/demo_book_daraqutni.json   # writes output/<pub_ref>/
uv run ilm-engine verify output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6
uv run pytest -q
```

The pipeline runs without any API key (`--llm null`); LLM-dependent items are then flagged for review. Use `--llm anthropic` or `--llm litellm` to enable model-based extraction.

## Documentation

| Document | Purpose |
|---|---|
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
| [docs/adr/](docs/adr/README.md) | Architecture decision records |
| [docs/tickets/](docs/tickets/BOARD.md) | Implementation tickets, dependency graph and execution waves |
