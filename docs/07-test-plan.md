# 07 — Test Plan

This plan covers: how the MVP is proven correct; how assignment §6 (technical considerations) is enforced by tests; and what "done" means for each ticket. FR/NFR IDs refer to `01-PRD.md`. EC IDs refer to `04-edge-cases.md`. Names follow `DECISIONS.md`.

---

## 1. Test pyramid

| Layer | Folder | Network | Purpose | Speed |
|---|---|---|---|---|
| Unit (`UT-*`) | `tests/unit/` | none | One function/module, synthetic + real snippets | < 5 s total |
| Golden (`GD-*`) | `tests/golden/` | none | Adapter input → canonical output, byte-compared | < 5 s |
| Invariant / property (`INV-*`) | `tests/invariants/` | none | Immutability, anchor validity, determinism, origin coverage | < 60 s |
| LLM fixture (`LLM-FX-*`) | `tests/llm/` | none (recorded) | Gateway, parsing, repair, evidence guard, consensus with recorded responses | < 5 s |
| Integration (`INT-*`) | `tests/integration/` | none | Full pipeline on the sample book, `llm.provider=null` and `fixture` | < 60 s (NFR-013) |
| Evaluation (`EV-*`) | `eval/` | none | Precision/recall against `eval/gold_index_sample.json` | < 30 s |
| Acceptance (`AT-*`) | `tests/acceptance/` | none | One test per PRD requirement area; uses integration outputs | < 60 s |
| Live LLM smoke (`LIVE-*`) | `tests/live/` | **yes**, opt-in (`-m live`, needs API key) | Real provider round-trip on 3 units | manual |

CI runs everything except `LIVE-*`. **No test may require network or an API key.**

## 2. Fixtures and test data

| Fixture | Content |
|---|---|
| `data/demo_book_daraqutni.json` | The real sample (read-only, never copied into tests with edits) |
| `tests/golden/shamela_v3/input_min.json` | A hand-cut 3-page subset of the sample (pages 21, 25, 33) |
| `tests/golden/shamela_v3/expected_canonical.json` | Expected `CanonicalBook` for the subset |
| `tests/golden/shamela_v3/input_v4_unknown.json` | Same subset with `schema_version: "4.0"` (EC-001) |
| `tests/golden/shamela_v3/input_renamed_field.json` | `b` renamed to `id` (EC-003) |
| `tests/fixtures/revision_r7.json` | Sample with `b000135` text changed and `b000590` removed (EC-012/013) |
| `tests/llm/recordings/*.json` | Recorded provider responses keyed by cache key: good, invented-quote, invalid-JSON, timeout, disagree, injection |
| `eval/gold_index_sample.json` | ≥ 30 persons hand-transcribed from PDF pp. 76–80 (فهرس الرواة المترجم لهم): name + printed page |

The recorded-fixture provider is `llm.provider = fixture` (a test-only provider that reads `tests/llm/recordings/`). It uses the same cache-key function as production. A missing recording fails the test loudly; it never falls through to the network.

## 3. Golden numbers for the sample book (single source for all tests)

These values were verified against the real file. Tests assert them **exactly** unless marked "≥".

| Quantity | Expected |
|---|---|
| pages held / `n` range | 68 / 3–72 |
| missing `n` | `[1, 2, 4, 18]` |
| claimed page count (card) | 72 (`٧٢`) |
| PDF pages / extra PDF pages | 80 / 73–80 (printed indexes) |
| blocks total | 594 |
| blocks by kind | text 260, footnote 317, heading 15, toc_heading 2 |
| blocks with `refs` / refs total | 150 / 300 |
| broken refs | 0 |
| distinct ref targets | 300 (no footnote targeted twice) |
| refs at `start: 0` | 59 |
| `continues` footnotes (all without marker) | 16 |
| footnotes not targeted by any ref | 17 (= 16 continuations + `b000215`) |
| refs originating from footnotes | 0 |
| nested footnotes linked by marker search | 1 (`b000215` → `b000210`, marker "أ") |
| logical footnote annotations after joining continuations | 301 (317 − 16) |
| sections (heading + toc_heading) / TOC entries | 17 / 17 |
| biographical entries | 75, numbered 1–75, no gap, no duplicate |
| entry #32 location | `b000294`, page 43 |
| entry-level (tarjama) footnotes | 74 (#32 has none → 1 `entry_without_footnote`) |
| span classes | c2 230, c5 64, c1 8, c4 2 |
| "صلى الله عليه وسلم" written / ﷺ glyph | 134 / 0 |
| `الدارقطني` variants | الدارقطني 28, الدَّارقطني 1, الدّارقطني 1 |
| internal ref `ترجمة رقم (٣٣)` | 1 (`b000063`, page 11) → resolves to entry 33 |
| `سيأتي` occurrences | 4 (unresolved forward refs) |
| hadith grading statements (`إسناده ضعيف/صحيح/حسن`) in footnotes | 4 (all `sensitive_content`) |
| top cited works | الإصابة 144, أسد الغابة 67, السير 59, الطبقات الكبرى 45, الطبقات 33, التهذيب 32, الاستيعاب 31 |
| origin: non-footnote blocks pages 3–16 / pages 17 + 19 / pages 20–72 | 77 / 13 / 187 (page 72's copyist tail goes to `transmission_isnad` via per-book YAML) |
| entry #8 anchor | `b000135`, length 102; `أسلمت` [60, 65); `ولم يُروَ عنها شيءٌ` [78, 97) |
| author death year | 385 AH, evidence `b000049` page 9 |
| sha256 of `data/demo_book_daraqutni.json` (prefix) | `2225272660a13e33…` |
| sha256 of `data/demo_book_daraqutni_v1.pdf` (prefix) | `3c220a2bc95e5a43…` |

## 4. Unit tests (selection; one test file per module)

| ID | Module | Asserts |
|---|---|---|
| UT-ADP-01 | `adapters/registry.py` | `(src-shamela, 3.0)` → `ShamelaV3Adapter` |
| UT-ADP-03 | registry | unknown `(source, version)` raises `UnknownSchemaVersion`, plus issue `unknown_schema_version` |
| UT-ADP-04 | `shamela_v3.py` | renamed field → validation error naming the field path |
| UT-ADP-05/06 | `shamela_v3.py` | missing optional → default; unknown key preserved in `raw_extras` |
| UT-ADP-08 | canonical | `volume` carried into anchors and IDs |
| UT-INT-01 | `integrity/hashing.py` | `block_hash` = sha256 of exact UTF-8 text; NFC/NFD variants give different hashes |
| UT-INT-02 | hashing | `source_declared_hash.verified == false` + `source_hash_unverified` issue |
| UT-DOC-01/02/03/05 | `document_analysis.py` | missing pages `[1,2,4,18]`, `page_count_mismatch`, PDF extra pages 73–80, `يتلوه`/second-part detection |
| UT-STR-02..05 | `structure.py` | TOC resolved via `source_ref.key` ("مقدمة المؤلف" → `n` 19); 17 sections; `title_variant` for الإخوة/الأُخوة |
| UT-ORG-01 | `origin.py` | `b000022` → `editor_text`; `b000093` → `transmission_isnad`; `b000098` → `author_text`; any footnote → `editor_footnote` |
| UT-MET-01..03 | `metadata.py` | card fields parsed; death 385 from `b000049` (with LLM fixture); "بن مهدي" alias conflict (EC-075) |
| UT-ANN-02..08 | `annotations.py` | continuation join (16); missing marker; nested `b000215`; broken ref synthetic; `start: 0` → `kind: tarjama` |
| UT-CIT-02..07 | `citations.py` | alias الطبقات; locator `(٨/ ١٥٧)` → {8, 157}; "الأصل" excluded; `ترجمة رقم (٣٣)` → entry 33; `سيأتي` unresolved; `رقم: ١٣٨٢` |
| UT-UNT-02..07 | `extractors/units.py` | multi-entry blocks; #32 mid-sentence; gap only after the second pass; editor lists pp. 6–12 excluded; #32 without footnote; cross-page join |
| UT-NAS-02..04 | `nlp/nasab.py` | `ابن قُرْط` mid-chain; markers stripped with offsets kept; kunya/ism/nisba split of "أبو الحسن علي بن عمر بن أحمد الدارقطني" |
| UT-NLP-01..09 | `nlp/normalize.py` | each normalization rule; char-map round trip; honorific token; digits; language detection |
| UT-ENT-02/03 | `entities.py` | three distinct هند entities; >1 authority candidate → `ambiguous_entity` |
| UT-REL-02..08 | `relations.py` | "ابنا أبي هالة" → #9, #10 `sibling_of {full}`, male; dual count mismatch penalty; `b000147` not a closure; `لأم ولد` → `mother_status: umm_walad` (`b000349`, `b000360`); `لأمه` → maternal (`b000502`); inferred `child_of` with `assertion: inferred`; "وقيل" alternatives |
| UT-EVD-02..04 | `validation/evidence.py` | exact match → 1.0; normalized match → 0.9 + mapped offsets; no match → 0 and `evidence_not_found` |
| UT-CON-02 | `consensus.py` | field-level disagreement → judge → `model_disagreement` if unresolved |
| UT-CNF-01 | `confidence.py` | worked examples from `06-ai-strategy.md §8`: 0.95, 0.90, 0.675 |
| UT-SEN-01/02 | `sensitivity.py` | `b000228` grading → `hadith_grading`; `c1` span → `prophetic_attribution`; always `pending_review` |
| UT-REV-03..05 | `review_queue.py` | two decisions → escalation; edit keeps the AI original; priority ordering |
| UT-LLM-05/06 | `llm/gateway.py` | chunking per unit; budget cap → `needs_llm` |
| UT-PUB-01..03 | `storage/json_store.py` | export excludes `pending_review`; every item has `origin`/`assertion`; stale anchor withheld |
| UT-SRC-02 | `search/lexical.py` | "الاخوة" finds blocks containing "الأُخوة"; highlight offsets on the original |

## 5. Golden tests

| ID | Asserts |
|---|---|
| GD-ADP-01 | `ShamelaV3Adapter(input_min.json)` == `expected_canonical.json` (byte-equal after canonical dump) |
| GD-ADP-02 | Template test, parameterized over every registered adapter: each must ship `input_*.json` + `expected_canonical.json`. A new adapter without goldens fails CI. |

Golden files are updated only through `uv run ilm-engine dev regen-goldens` together with an adapter version bump (EC-006).

## 6. Invariant / property tests (assignment §6)

| ID | §6 requirement | Test |
|---|---|---|
| INV-01 | Original content untouched | sha256 of every file under `data/` (and `store/originals/`) is equal before and after `ilm-engine run`. The store copy has mode 0444. A monkeypatched `open(..., "w")` on `data/` raises. |
| INV-02 | Every unit traceable | For every anchor in every output file: block exists; `block.text[start:end] == quote`; `block_hash` matches. Coverage: 100% of units, facts and annotations have ≥ 1 anchor. |
| INV-03 | Repeatable | Run twice with the same config (provider `null` and `fixture`). Every output file is byte-identical except `run_manifest.json` timestamps/run_id. IDs are identical. |
| INV-04 | Repeatable under config change | Threshold change → only `review_status` fields differ; extraction outputs are identical (re-score, not re-extract) |
| INV-05 | Author vs AI distinguished | 100% of records carry `origin` ∈ DECISIONS §6 and facts carry `assertion`. Every `inferred` fact has `origin == ai_generated`. |
| INV-06 | Enrichment separate & linked | No output file contains full block text except `quote` fields and `search_index.json`'s normalized copy. Every record links by `block_id`. |
| INV-07 | Modular | Import-graph test: `processors/*`, `extractors/*` and `validation/*` import only `canonical.models`, never `adapters.*` |
| INV-08 | Confidence + human approval | Every LLM-derived record has `extraction.confidence` and `review_status`. Every sensitive record is `pending_review` (or a human status). |
| INV-09 | IDs deterministic | `ids.py` gives the same ID for the same `(pub_ref, natural key)` across processes |
| PROP-01 | Normalizer | Hypothesis-based: for random Arabic strings, the char-map maps every normalized index back into a valid original index; normalization is idempotent |

## 7. LLM fixture tests

| ID | Recording | Expected |
|---|---|---|
| LLM-FX-01 | good extraction for entry #9/#10 | `sibling_of {full}` accepted; confidence 0.90 with two-model agreement |
| LLM-FX-02 | quote "هند بنت عتيق روت حديثًا" (not in source) | fact rejected, `evidence_not_found` (EC-090) |
| LLM-FX-03 | invalid JSON then valid on repair | `schema` 0.9; second invalid → `schema_invalid` |
| LLM-FX-04 | 429 ×3 | backoff calls = 3, then `needs_llm` (EC-092) |
| LLM-FX-05 | model A full, model B maternal, judge unresolved | `model_disagreement` + review item showing both |
| LLM-FX-06 | source containing an injection string | output still schema-valid; no instruction followed; evidence guard passes or rejects |
| LLM-FX-07 | cache | second call with the same key performs 0 provider calls |
| LLM-FX-08 | prompt version bump | new cache key; manifest lists the new prompt version |

## 8. Integration tests

| ID | Scenario | Expected |
|---|---|---|
| INT-RUN-01 | `ilm-engine run --input data/demo_book_daraqutni.json --pdf data/demo_book_daraqutni_v1.pdf --out output/ --llm null` | exit 0; all DECISIONS §10 files present (`graph.html` optional); golden numbers §3 hold; under 60 s |
| INT-RUN-02 | fixture provider fails at step `llm_extract` | status `partial`; re-run resumes; deterministic outputs unchanged |
| INT-RUN-03 | no API key | `needs_llm` items are in `review_queue.json`; run succeeds |
| INT-RUN-04 | `ilm-engine verify output/<pub_ref>` | re-checks INV-01/02 on existing outputs; exit 0 |
| INT-REV-01..03 | run r6, then `revision_r7.json` | unchanged-block enrichment kept; `b000135` anchors `anchor_stale`; `b000590` anchors stale; only affected units re-processed |
| INT-REV-04 | `review_decisions.json` applied via `ilm-engine review apply` | statuses updated; audit entries written; approved/edited exported to `training_examples.jsonl` |
| INT-SRC-01 | `ilm-engine search "الاخوة من ولد العباس"` | top hit is the section of heading `b000339`; result carries an anchor |

## 9. Evaluation (EV)

| ID | Metric | Method | MVP target |
|---|---|---|---|
| EV-01 | Person entity recall vs printed index sample | Normalized-name match of `entities.json` persons against `gold_index_sample.json` (with page tolerance ±1) | ≥ 0.90 |
| EV-02 | Person entity precision (on the sample's page range) | Extracted persons on gold pages that appear in the gold list | ≥ 0.80 (the index lists only persons with a tarjama; mentions inflate false positives, so precision is computed on entry persons) |
| EV-03 | Calibration | Reliability table of confidence buckets vs reviewer outcomes (once decisions exist) | report only |
| EV-04 | Evidence accuracy | % of facts whose quote verifies | 100% (hard gate) |
| EV-05 | Entry segmentation | 75/75 entries with correct number and block | 100% |

`ilm-engine eval output/<pub_ref>` writes `eval_report.json` with these numbers; the MVP report quotes them.

## 10. Acceptance tests (map to PRD)

| AT | PRD area / FR | Given → Then |
|---|---|---|
| AT-001 | Ingestion & adapters FR-001..004 | sample JSON → `ShamelaV3Adapter` used; manifest records adapter + version; unknown version fails closed |
| AT-002 | Integrity FR-010..012, NFR-001 | INV-01 + INT-REV-01 pass |
| AT-003 | Metadata FR-020..022 | `metadata.json` has title, author (+ death 385 with anchor `b000049` when LLM enabled, else `needs_llm`), editor, publisher, edition, 1413/1993, category; conflicts list contains `page_count_mismatch` (missing pages classified), `title_variant`, author alias "بن مهدي" |
| AT-004 | Book family FR-030..033 | `related_works.json` contains: cited works (≥ 7 distinct `wrk_*`, top 7 counts as §3), `same_topic_as` Abu Dawud's "الأخوة الذين روي عنهم الحديث" from `b000018`; schema supports all 8 work relation types |
| AT-005 | Indexing FR-040..043 | `structure.json` has 17 sections with block ranges; TOC aligned via Shamela key; 75 units |
| AT-006 | Arabic NLP & search FR-050..053 | normalized search copy, original untouched; variant query hit (INT-SRC-01); morphology fields present (`approximate` if CAMeL is absent) |
| AT-007 | Annotations FR-060..063 | 300 links, 16 joins, 1 nested link, 1 internal ref resolved, 4 unresolved `سيأتي`, citations with locators |
| AT-008 | Genre extraction FR-070..073 | genre `biography/ansab` + secondary `hadith`; biography units for 75 entries; ≥ 1 `hadith_takhrij` unit (from `b000228`) in review |
| AT-009 | Knowledge graph FR-080..083 | #9/#10 `sibling_of {full}`; three distinct هند; `umm_walad` on `b000349` children; `graph.html` or nodes/edges JSON exported |
| AT-010 | Validation FR-090..093 | evidence guard (LLM-FX-02), consensus (LLM-FX-05), confidence worked examples (UT-CNF-01) |
| AT-011 | Human review FR-100..102 | `review_queue.json` items contain original text, value, anchors with `scan_page`, model outputs, confidence, issues; apply-decisions flow works (INT-REV-04) |
| AT-012 | Storage & publishing FR-110..112 | `enrichment.json` + `enrichment.db` consistent (same record counts); publish export excludes pending; every fact resolves to a `scan_page` |
| AT-013 | Orchestration & AI FR-120..123 | DAG resume (INT-RUN-02); provider switch via config only; `training_examples.jsonl` written |
| AT-014 | Deliverables FR-130 | `deliverables/Technical_Proposal.md` exists with all 8 assignment deliverable sections; diagrams render (`mmdc` exit 0); MVP numbers in the proposal equal `eval_report.json` |
| AT-015 | NFR-003/005 | INV-03, INV-05 pass |
| AT-016 | NFR-004 modularity | INV-07 + a dummy adapter `adapters/dummy_v1.py` registered in a test runs the full pipeline with no core edits |

## 11. Commands

```bash
cd mvp
uv sync
uv run ruff check .
uv run pytest                          # all offline tests
uv run pytest -m "not live" -q         # CI default
uv run pytest tests/invariants -q      # §6 guarantees only
uv run pytest -m live                  # opt-in, needs ANTHROPIC_API_KEY (+ second provider key)
uv run ilm-engine run --input data/demo_book_daraqutni.json --pdf data/demo_book_daraqutni_v1.pdf --out output/ --llm null
uv run ilm-engine verify output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6
uv run ilm-engine eval output/pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6 --gold eval/gold_index_sample.json
```

## 12. Exit criteria for the MVP

1. All tests except `LIVE-*` pass; ruff is clean.
2. INV-01..INV-09 pass (assignment §6 proven).
3. The golden numbers in §3 are reproduced.
4. EV-04 = 100%, EV-05 = 100%, EV-01 ≥ 0.90.
5. Two consecutive runs are byte-identical (INV-03).
6. AT-001..AT-016 pass.
