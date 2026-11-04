# Submission checklist

Each deliverable of the assignment (§5), where it is, and how it was verified.

| # | Deliverable | Where | Verified by |
|---|---|---|---|
| 1 | System architecture diagram | [diagrams/system-architecture.png](diagrams/system-architecture.png) ([.svg](diagrams/system-architecture.svg), [.mmd](diagrams/system-architecture.mmd)); [Proposal §1](Technical_Proposal.md#1-system-architecture) | Renders with mermaid-cli (`bash deliverables/diagrams/render.sh`) |
| 2 | Automation and data-flow diagram (agents, scripts, databases, human review) | [diagrams/data-flow.png](diagrams/data-flow.png), [agent-workflow.png](diagrams/agent-workflow.png), [adapter-flow.png](diagrams/adapter-flow.png); [Proposal §2](Technical_Proposal.md#2-data-flow-and-automation) | All 12 assignment steps numbered in the diagram |
| 3 | Technology recommendations with purposes | [Proposal §3](Technical_Proposal.md#3-technology-recommendations) | MVP vs production per concern |
| 4 | Arabic NLP and AI model strategy (commercial and open-weight) | [Proposal §4](Technical_Proposal.md#4-arabic-nlp-and-ai-model-strategy); [docs/06-ai-strategy.md](../docs/06-ai-strategy.md) | Normalizer, nasab parser, evidence guard and consensus are tested |
| 5 | Knowledge extraction approach (genre-specific, NER, source-location mapping) | [Proposal §5](Technical_Proposal.md#5-knowledge-extraction-approach) | Seven genre schemas exported in [schemas/](../schemas/); anchors re-verified every run |
| 6 | Model training approach (datasets, fine-tuning, LoRA/PEFT) | [Proposal §6](Technical_Proposal.md#6-model-training-approach) | Review loop already exports `training_examples.jsonl` |
| 7 | MVP on the sample PDF and JSON | Repository root; [Proposal §7](Technical_Proposal.md#7-mvp-on-the-sample-book) | `uv run ilm-engine run --input data`; 680 tests (`uv run pytest -q`) |
| 7a | Metadata extraction | `output/<pub_ref>/metadata.json` | `tests/test_metadata_*.py` |
| 7b | Structural indexing | `structure.json` | `tests/test_structure.py`, `test_toc_alignment.py`, `test_section_ranges.py` |
| 7c | Knowledge-unit extraction | `knowledge_units.json` | `tests/test_entries.py`, `test_units.py`, `test_unit_facts.py` (75/75 entries) |
| 7d | Entity and relationship identification | `entities.json`, `relationships.json` | `tests/test_entities.py`, `test_alias.py`, `test_sibling_groups.py`, `test_relation_kinds.py`, `test_inferred_relations.py`; `ilm-engine eval` (P = R = 1.0) |
| 7e | Source-location mapping | Anchors in every output | `tests/test_invariants.py`; `ilm-engine verify` |
| 7f | Structured JSON output | `enrichment.json` (+ [schema](../docs/enrichment.schema.json)) | `tests/test_enrichment_json.py` |
| 8 | Implementation roadmap (phases, challenges, infrastructure, resources) | [Proposal §8](Technical_Proposal.md#8-implementation-roadmap); [docs/08-roadmap.md](../docs/08-roadmap.md) | — |

## Technical considerations (§6)

| Consideration | Where it is shown |
|---|---|
| Original content untouched | [Proposal compliance table](Technical_Proposal.md#technical-considerations-compliance); `tests/test_invariants.py`, `tests/test_e2e.py` |
| Enrichment stored separately and linked | `output/<pub_ref>/`, `enrichment.db` (hashes only) |
| Every unit traceable | Anchors with verbatim quotes; `integrity_verify` step |
| Author vs AI distinguished | `origin` and `assertion` on every record |
| Modular, repeatable, scalable | Adapters ([docs/ADAPTERS.md](../docs/ADAPTERS.md)), genre plugins, byte-identical reruns (`tests/test_e2e.py`) |
| Confidence and human approval | `validation_report.json`, `review_queue.json`, `review.html`, `ilm-engine review apply` |

## Before submitting

- [ ] `uv sync && uv run pytest -q` passes (needs the sample files in `data/`)
- [ ] `uv run ilm-engine run --input data` completes and `review.html` opens
- [ ] `bash deliverables/diagrams/render.sh` has been run after any diagram change
- [ ] The sample data and the adapter golden excerpt stay out of the repository (both are git-ignored)
