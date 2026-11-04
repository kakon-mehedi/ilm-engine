# ILM Engine

**Post-OCR knowledge enrichment for digitized Islamic books.**

ILM Engine turns a digitized book (structured JSON + page scans) into a separate, traceable **enrichment layer**: metadata, structure, footnotes, citations, knowledge units, people, relationships, search and a knowledge graph. Every item points back to its exact source location; the original is never modified.

## Quick start

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/). Put the sample book (`demo_book_daraqutni.json` and `demo_book_daraqutni_v1.pdf`) into `data/` first; it is confidential and not committed.

```bash
uv sync
uv run ilm-engine serve              # web UI on http://127.0.0.1:8000/
uv run ilm-engine run --input data   # or run the pipeline from the terminal
```

**Web UI:** upload the book JSON (and PDF), watch the 21 pipeline steps run, review uncertain and sensitive items next to the highlighted source text, and explore the results: entries, people, relationships, graph, search and downloads.

## Commands

| Command | Purpose |
|---|---|
| `ilm-engine serve` | Start the web UI |
| `ilm-engine run --input data` | Run the pipeline on a book (`--quiet`, `--no-cache`, `--llm anthropic`) |
| `ilm-engine eval` | Precision and recall against the printed index |
| `ilm-engine search "الدارقطني"` | Arabic-aware search |
| `ilm-engine verify output/<pub_ref>` | Re-check original files, outputs and every source anchor |
| `ilm-engine review apply decisions.json --book <pub_ref>` | Apply reviewer decisions |
| `uv run pytest -q` | Run the tests |

Prefix each with `uv run`. No API key is needed: without a model, LLM-dependent work is flagged for review.

## How it works

```mermaid
flowchart LR
    IN["Book JSON + PDF"] --> AD["Source adapter"]
    AD --> CB["Canonical book<br/>(read-only, hashed)"]
    CB --> P["Processing<br/>structure · origin · metadata<br/>footnotes · citations"]
    P --> X["Extraction<br/>knowledge units · people<br/>relationships"]
    X --> V["Validation<br/>evidence · confidence"]
    V -->|confident| E["Enrichment layer"]
    V -->|uncertain / sensitive| R["Human review"]
    R --> E
    E --> S["Search · graph · export"]
```

- **Untouched originals:** inputs are stored read-only and re-hashed after every run.
- **Traceable:** each record carries an anchor (page, block, offsets, verbatim quote); quotes that do not match the source are rejected.
- **Author vs AI:** every record is labelled with its origin (author, isnad, editor, AI) and whether it is stated or inferred.
- **Human approval:** low-confidence items go to review; sensitive ones (hadith grading, fiqh rulings) need a scholar.
- **Repeatable:** deterministic IDs and caching give byte-identical reruns.

## Outputs

Written to `output/<pub_ref>/`. The main file is `enrichment.json` ([schema](docs/enrichment.schema.json)); the same data is split into `metadata.json`, `structure.json`, `knowledge_units.json`, `entities.json`, `relationships.json`, `citations.json` and more, alongside `graph.html`, `review_queue.json` and `run_manifest.json`.

## Repository

```
src/ilm_engine/   pipeline code and web UI
config/           thresholds and per-book settings
tests/            unit, golden and end-to-end tests
deliverables/     technical proposal and diagrams
docs/             requirements, architecture, decisions, tickets
data/             sample input (git-ignored)
```

## Documentation

- [Technical proposal](deliverables/Technical_Proposal.md): architecture, AI strategy, results and roadmap
- [Architecture](docs/02-architecture.md) and [diagrams](deliverables/diagrams/)
- [Pipeline walkthrough](docs/README.md)
- [Adding a source format](docs/ADAPTERS.md)
