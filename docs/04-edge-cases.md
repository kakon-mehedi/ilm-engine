# 04 — Edge-Case Analysis

Every edge case has an ID, a scenario, an example (real = verified against `data/demo_book_daraqutni.json` with `python3 -I`; hypothetical = marked *hyp.*), detection, handling, the issue code from `DECISIONS.md §9` (or `—` when the case is handled silently and only logged), and the test that covers it (`07-test-plan.md`).

Rule for all cases: **fail closed on input/integrity problems, degrade gracefully on enrichment problems.** An unknown input format stops the book. A failed extraction only produces an issue and a review item; the rest of the book still processes.

---

## A. Input, adapters & schema changes

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-001 | Unknown `schema_version` | *hyp.* Shamela export arrives with `revision.content.schema_version = "4.0"` (sample is `3.0`) | `adapters/registry.py` has no entry for `(src-shamela, 4.0)` | Stop this book before any processing. Do not guess the closest adapter. Record the run as `failed_input`. | `unknown_schema_version` | UT-ADP-03 |
| EC-002 | Brand-new source format | *hyp.* JSON from the in-house OCR team (`source_code: src-ocr-team`) | No adapter registered for the `source_code` | Same as EC-001. A new adapter is added (`adapters/<source>_v<N>.py`), registered, and given golden files. No code after the adapter changes. | `unknown_schema_version` | UT-ADP-03, GD-ADP-02 |
| EC-003 | Field renamed or moved in a known version | *hyp.* `blocks[].b` renamed to `blocks[].id` | Adapter's Pydantic input model fails validation, or a required canonical field is empty | Fail closed and list the missing or renamed paths in the error. Fix it by bumping the adapter version, never by silent fallback. | `unknown_schema_version` | UT-ADP-04 |
| EC-004 | Optional field missing | Real: 112 text blocks have no `refs` and no `spans`. Real: `quality.manual = {}`. | Optional in the input model | Canonical default (empty list or `null`). No issue raised. | — | UT-ADP-05 |
| EC-005 | Unknown extra fields | *hyp.* a new key `blocks[].confidence_ocr` appears | Input model allows extras and collects them | Copied unchanged to `raw_extras` on the canonical object. Nothing is lost, and downstream steps ignore it. | — | UT-ADP-06 |
| EC-006 | Adapter version upgrade changes the canonical output | Real: the source itself has `revision.origin = adapter_upgrade`, `adapter_semver 1.3.0` | Golden-file diff in CI | A golden-file change must be reviewed and committed together with an adapter version bump. `run_manifest.json` records the adapter and its version. | — | GD-ADP-01 |
| EC-007 | Scanned-only book, no JSON | *hyp.* only a PDF arrives | No structured text input | Out of scope (OCR belongs to another team). The book is rejected and goes back to the OCR queue. The architecture keeps a placeholder `OcrAdapter` slot. | `unknown_schema_version` | UT-ADP-07 |
| EC-008 | Non-Arabic or mixed-language book | *hyp.* an Urdu or English translation | Language detection on a sample of blocks (`nlp/normalize.py` script ratio) | The Arabic-only normalizer is skipped. `language` is recorded on the book. Extraction uses a language-specific prompt variant. For `translation_of` see EC-071. | — | UT-NLP-09 |
| EC-009 | Multi-volume book | *hyp.* `volume_count: 4` (sample has 1) | `pages[].volume > 1` | Anchors already carry `page` and `scan_page`. Volume is added to the anchor (`volume` field, default 1). Sections may span volumes. IDs include the volume. | — | UT-ADP-08 |

## B. Integrity & revisions

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-010 | Someone or something tries to modify the original | *hyp.* a bug writes to `data/` | Hash of every file in `data/` taken before and after each run | Run fails. Originals are opened read-only, and the store copies them into `store/originals/<pub_ref>/` with file mode 0444. | — | INV-01 |
| EC-011 | Source-declared hash cannot be reproduced | Real: `content_sha256 = 1f974e…` does not match any of 6 tried canonicalizations of `content` / `pages` | Recompute and compare | Keep it as `source_declared_hash` with `verified: false`. Compute our own `canonical_content_hash`. Open question to the client. | `source_hash_unverified` | UT-INT-02 |
| EC-012 | New revision (r6 → r7) with some blocks changed | *hyp.* `b000135` gets a corrected spelling | Per-block `block_hash` comparison between revisions | Unchanged blocks keep their enrichment (re-anchored to `@r7`). Anchors on changed blocks become `stale` and their units go back to `pending_review`. Only changed blocks and their dependents are reprocessed. | `anchor_stale` | INT-REV-01 |
| EC-013 | Block deleted in a new revision | *hyp.* `b000590` (`* * * * *`) removed in r7 | Block ID present in r6, absent in r7 | Anchors on the deleted block become `stale`, and the units are flagged for review. Never re-point them automatically to the "nearest" block. | `anchor_stale` | INT-REV-02 |
| EC-014 | Block IDs renumbered in a new revision | *hyp.* source re-exports with new IDs | Many IDs missing while text hashes still exist under other IDs | Re-map by `block_hash` (exact text match, same page). If the mapping is ambiguous (duplicate texts), mark the anchor stale. | `anchor_stale` | INT-REV-03 |
| EC-015 | Offsets computed on normalized text | *hyp.* an extractor returns offsets from `normalized_text` (diacritics stripped, so all indices shift) | Anchor invariant `text[start:end] == quote` fails on the original | Offsets are **only** computed on the original text (DECISIONS §4). The evidence guard re-locates the quote on the original. If it is found only after normalization, `evidence = 0.9` and the offsets are mapped back through a char-index map. | `evidence_not_found` (if no map) | INV-02, UT-EVD-03 |
| EC-016 | Duplicate run of the same book | Real: running the sample twice | Same input hashes + config hash + prompt versions | Deterministic IDs and cached LLM responses give byte-identical outputs. Outputs are overwritten idempotently, never appended. | — | INV-03 |
| EC-017 | Partial failure mid-book | *hyp.* LLM provider down while processing page 40 | Step returns an error | Each step is cached by input hash, so a re-run resumes from the failed step. Deterministic steps (structure, annotations, units) are already complete and kept. The book status becomes `partial` with the list of failed steps. | `needs_llm` | INT-RUN-02 |

## C. Pages, structure & TOC

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-020 | Claimed page count ≠ held pages | Real: card says ٧٢, JSON holds 68 pages; source quality says short 5.6% vs tolerance 5% yet `passed: true` | `document_analysis.py` compares `metadata.source_attributes.page_count` with `len(pages)` and lists the missing `n` | Report the exact missing numbers instead of a percentage. | `page_count_mismatch` | UT-DOC-01 |
| EC-021 | Missing pages are non-content | Real: missing `n` = 1, 2, 4, 18. PDF shows cover, publisher/copyright page, basmala page, blank page. | Missing list, plus optional check of the scan page | Classify each missing page (`front_matter` or `unknown`). For this book the report says "no content lost". Page 2's publisher data exists only in the scan, so it is noted as a metadata source. | `missing_page` (severity `info`) | UT-DOC-02 |
| EC-022 | PDF has more pages than JSON | Real: PDF 80 pages vs JSON `n` max 72. PDF pp. 73–80 are printed indexes (فهرس الأحاديث, فهرس الرواة المترجم لهم, الفهرس الإجمالي). | `pdf_page_count > max(scan_page)` | Report it. These pages are not content to enrich. They are used only as the **evaluation gold source** (`eval/gold_index_sample.json`). | — | UT-DOC-03 |
| EC-023 | PDF page ≠ JSON page | Real: here `scan_page == n == PDF page` for all 68 pages. *hyp.* another book with a scan offset. | Compare `scan_page` with `n`. Spot-check a rendered page. | Always anchor with both `page` (printed) and `scan_page` (PDF). The viewer uses `scan_page`. | — | UT-DOC-04 |
| EC-024 | TOC `source_page` is not the printed page, and the offset varies | Real: TOC "مقدمة المؤلف" `source_page` 15 sits on `n` 19. The offset between Shamela key and `n` changes 2 → 3 → 4 along the book. | TOC entries never match `n` reliably | Resolve each TOC entry through `pages[].source_ref.key`, never through `n` or a fixed offset. | `toc_page_offset` (info) | UT-STR-02 |
| EC-025 | TOC entry with no matching block | Real: `source_extras` lists "مقدمة المحقق" (page 5) and "مقدمة المؤلف" (page 19), placed as `toc_heading` by the source adapter | `toc_heading` kind, or a TOC title not found among the page's headings | Create the section from the TOC entry and anchor it to the first block of that page. | `toc_without_block` (info) | UT-STR-03 |
| EC-026 | Heading not present in TOC | Real: 15 headings + 2 toc_headings vs 17 TOC entries. Match by normalized title. | Heading with no TOC match | Keep it as a section with `source: heading_only`. | `heading_without_toc` | UT-STR-04 |
| EC-027 | Title spelling differs between TOC, heading and card | Real: الإخوة (card) vs الأُخوة (page 3 title, 35×) vs الاُخوة (1×). "عملي فى الكتاب" uses ى for ي. | Compare after normalization | Match on normalized form. Keep every surface form as an alias. | `title_variant` | UT-STR-05 |
| EC-028 | Book continues in a missing part | Real: page 72 `b000585` "يتلوه في الذي يليه" and footnote `b000591` "لم أجد الجزء الثاني". This is volume 1 of 2, and the second part was never found. | Pattern list (`يتلوه`, `الجزء الثاني`) | Mark the book `part_of_series: incomplete`. The last section is open-ended. | `metadata_conflict` (info) | UT-DOC-05 |

## D. Numbering & knowledge-unit entries

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-030 | Several entries in one block | Real: `b000217` "١٨ - حمزة. … ١٩ - والعباس."; `b000256` holds 22–24 | Entry regex `(?<![٠-٩(/])([٠-٩]+) ?- ` run over the whole block, not only `^` | Split into one unit per match. Each unit's anchor covers its own char range. | — | UT-UNT-02 |
| EC-031 | Entry number mid-sentence | Real: #32 in `b000294` "٣١ - وأُمية. … وأختهم: ٣٢ - أروى؛ بنو الحارث…". A naive `(?:^\|… )` regex misses it and reports a false gap. | Correct regex finds it | All 75 entries (1–75) are found. Lesson recorded: a gap triggers a second-pass search before being flagged. | — | UT-UNT-03 |
| EC-032 | Numbering gap or duplicate | *hyp.* (none in sample after EC-031) | Sequence check after the second pass | Flag the gap only if a re-scan with a relaxed pattern also fails. | `numbering_gap` / `numbering_duplicate` | UT-UNT-04 |
| EC-033 | Numbered lists in the editor intro are not entries | Real: pages 6–12, e.g. `b000022` "١ - هذا الكتاب خاص بالصحابة…", `b000027` "١ - حقَّقت النّص…" (the numbering restarts) | Origin = `editor_text` | Entry detection runs only on `author_text` blocks from page 21. The editor lists become `editor_note` units at most. | — | UT-UNT-05 |
| EC-034 | Entry without its tarjama footnote | Real: 74 entry-level footnotes (marker `N -`). #32 (أروى) has none. | Entry number with no ref from `start: 0` and no footnote with marker `٣٢ -` | Unit is still created. The coverage report lists it. | `entry_without_footnote` (info) | UT-UNT-06 |
| EC-035 | Entry text continues on the next page | *hyp./real candidate:* body blocks without final punctuation (66 such blocks) | Last author block on a page without terminal punctuation, followed by a non-entry first block | Join into one unit with multiple anchors (one per block). Never concatenate the stored text. | — | UT-UNT-07 |

## E. Annotations & footnotes

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-040 | Footnote continues from the previous page | Real: 16 footnotes with `continues: true`, e.g. `b000103` (p.20) starting with "=" | `continues` flag | Join it to the last footnote of the previous page as one annotation with 2 anchors. | `continued_footnote_joined` (info) | UT-ANN-02 |
| EC-041 | Footnote without a marker | Real: exactly the 16 continuation footnotes have no `marker` | `marker` missing | Treated as a continuation (EC-040). If `continues` is false and there is no marker, it becomes a standalone annotation and is flagged. | `unlinked_footnote` | UT-ANN-03 |
| EC-042 | Nested footnote (footnote of a footnote) | Real: `b000215` (p.33, marker "أ") is the note for "(أ)" inside footnote `b000210`. The JSON has 0 refs originating from footnotes. | Footnote not targeted by any ref, with an alphabetic marker | Search footnotes on the same page for "(marker)". If exactly one match, link with `link_method: marker_search` and confidence 0.9. | `nested_footnote` | UT-ANN-04 |
| EC-043 | Footnote not referenced by anything | Real: 17 footnotes unreferenced = 16 continuations + `b000215`. *hyp.* a true orphan. | No ref, not a continuation, nested search fails | Standalone annotation → review. | `unlinked_footnote` | UT-ANN-05 |
| EC-044 | Ref points to a missing block | Real: 0 of 300 refs broken. *hyp.* `to: b999999`. | Target lookup | Drop the link, keep the source span, raise an issue. | `broken_ref` | UT-ANN-06 |
| EC-045 | Ref span does not contain the marker | *hyp.* ref `start/end` text ≠ "(N)" | Compare `text[start:end]` with the footnote marker | Keep the link and lower its confidence. | `broken_ref` (warn) | UT-ANN-07 |
| EC-046 | Ref at `start: 0` (entry number → tarjama footnote) | Real: 59 refs start at 0, e.g. `b000105` "١ - فاطمة." → `b000109` | `start == 0` and the target marker matches `N -` | Typed as `annotation.kind = tarjama` (biography note of the entry's person). This is the primary evidence source for the person's facts (`editor_footnote`). | — | UT-ANN-08 |

## F. Citations & internal references

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-050 | Same work cited under different short names | Real: "الطبقات الكبرى" (45) vs "الطبقات" (33). "التهذيب" may be تهذيب التهذيب or تهذيب الكمال. | Title normalization + alias table | Map to a `wrk_` ID through an alias table. Ambiguous short names stay `candidates[]` → review. | `ambiguous_entity` | UT-CIT-02 |
| EC-051 | Citation with volume/page locator | Real: "الإصابة (٨/ ١٥٧)" | Regex for `(vol/ page)` after a quoted title | Store `locator: {volume: 8, page: 157}` with Arabic digits converted. | — | UT-CIT-03 |
| EC-052 | "الأصل" is the manuscript, not a book | Real: "الأصل" 14× (e.g. `b000594` "كذا في الأصل") | Stop-list | Not a cited work. It is `manuscript_reference`. | — | UT-CIT-04 |
| EC-053 | Internal reference to another entry | Real: `b000063` (p.11) "مثل ترجمة رقم (٣٣)" | Pattern `ترجمة رقم \(N\)` | Link to the unit with `entry_no = 33`. | `unresolved_internal_ref` (if no target) | UT-CIT-05 |
| EC-054 | Forward reference without a target | Real: `b000226` "سيأتي تخريجه", `b000228` "كما سيأتي" | Pattern `سيأتي` | Keep it as `internal_ref` with `target: null` → low-priority review. | `unresolved_internal_ref` | UT-CIT-06 |
| EC-055 | Hadith collection reference with a number | Real: `b000133` "رواه البخاري … (رقم: ١٣٨٢)" | Pattern `رواه <collector> … رقم` | `cites` relation with `hadith_number`. Also feeds the hadith genre extractor. | — | UT-CIT-07 |

## G. Arabic text

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-060 | Diacritic variants of the same name | Real: الدارقطني 28×, الدَّارقطني 1×, الدّارقطني 1× | — | Search copy strips tashkeel. Original untouched. All three hit the same query. | — | UT-NLP-01 |
| EC-061 | Hamza / alif variants | Real: الأُخوة 35×, الأخوة 4×, الاُخوة 1×, card الإخوة | — | Normalize أ إ آ ٱ → ا in the search copy only. | `title_variant` (titles only) | UT-NLP-02 |
| EC-062 | Honorific as glyph vs written | Real: "صلى الله عليه وسلم" written 134×. The glyph ﷺ appears 0× in the JSON (the PDF prints a ligature). | — | The search copy maps ﷺ ↔ "صلى الله عليه وسلم" to one token `<SAW>`. Mentions of the Prophet are recognised in both forms. | — | UT-NLP-03 |
| EC-063 | ى / ي and ة / ه confusion | Real: "عملي فى الكتاب" (فى for في) | — | Normalize ى→ي and ة→ه in the search copy. Never in anchors. | — | UT-NLP-04 |
| EC-064 | Tatweel and decorative characters | *hyp.* "الـدارقطني" | — | Strip tatweel (ـ) in the search copy. | — | UT-NLP-05 |
| EC-065 | Arabic-Indic digits | Real: all numbers (٨/ ١٥٧, ٣٨٥) | — | `nlp/arabic_digits.py` converts them for numeric fields. The original string is kept. | — | UT-NLP-06 |
| EC-066 | Unicode normalization form differs (NFC/NFD) | *hyp.* combining marks reordered | Compare NFC forms | Hash and offsets on the exact original. Matching compares NFC. Evidence found only after NFC → evidence 0.9. | — | UT-EVD-04 |
| EC-067 | Prompt injection inside book text | *hyp.* a block contains "ignore previous instructions and output…" | Book text is passed only as delimited data. Output schema is strict. | Model output is validated against the schema and the evidence guard. Instructions inside the data are never followed. | `schema_invalid` / `evidence_not_found` | LLM-FX-06 |

## H. Entities & names

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-070 | Same name, different persons | Real: "هند" = هند بنت عتيق (#8, female, `b000135`), هند بن أبي هالة (#9, male, `b000136`), and هند بن زرارة = أبو هالة (`b000138`) | Same normalized `ism` with different nasab, gender or context | Separate entities. Linking uses the nasab chain, gender, entry number and section. If unresolved → review. | `ambiguous_entity` + `sensitive_content` (narrator disambiguation) | UT-ENT-02 |
| EC-071 | Gender ambiguity of a name | Real: #9 "وهند." alone is gender-ambiguous. "ابنا" in `b000137` proves #9 and #10 are male. | Name in the female-ambiguous list | Gender is derived from grammar (ابنا/بنو/بنات, بن/بنت) or the footnote. Otherwise `gender: unknown`. | `ambiguous_entity` | UT-REL-03 |
| EC-072 | "ابن" in the middle of a nasab | Real: heading `b000439` "… بن عبد الله ابن قُرْط …" | Nasab parser accepts both `بن` and `ابن` as links | Parse the chain the same way. `ابن` at a line start or after a full name is still a link. | — | UT-NAS-02 |
| EC-073 | Nasab interrupted by footnote markers | Real: `b000135` "بن عابد (١) بن عبد اللَّه" | Markers `(N)` inside the chain | Strip markers for parsing, keep the original offsets. | — | UT-NAS-03 |
| EC-074 | Kunya / laqab / nisba forms | Real: "أبو الحسن علي بن عمر بن أحمد الدارقطني", "أبو هالة" | Parser rules | Split into `kunya`, `ism`, `nasab[]`, `nisba`. All surface forms become aliases. | — | UT-NAS-04 |
| EC-075 | Author name differs between card and text | Real: page 17 `b000083` adds "بن مهدي" to the card's name | Compare normalized chains | Merge as aliases of one entity. Record the longer chain as `full_name_as_text`. | `metadata_conflict` (info) | UT-MET-03 |
| EC-076 | Narrator disambiguation needed for linking to an authority list | *hyp.* "محمد بن عبد الواحد" matches 3 narrators in the authority DB | >1 candidate | Never auto-pick. Candidates with scores → review. | `ambiguous_entity` + `sensitive_content` | UT-ENT-03 |

## I. Relations

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-080 | Dual "ابنا" closes a sibling group | Real: `b000137` "١٠ - وهالة؛ ابنا أبي هالة" → #9 + #10 | Closing-phrase pattern (ابنا/بنو/بنات/ابنتا + father) | Group = preceding entries back to the group start. Dual means exactly 2 members. | — | UT-REL-02 |
| EC-081 | Dual count does not match the group | *hyp.* "ابنا" but 3 preceding entries | Count check | Penalty ×0.7 → review. | `ambiguous_entity` | UT-REL-04 |
| EC-082 | "ابنا" meaning "two sons of X", not a group closure | Real: `b000147` "روى عنه ابنا (١) أختِه الحسن والحسين" | Not in an entry line, and followed by a noun other than a father | Not a sibling closure. Handled by the LLM relation extractor (`needs_llm` if no LLM). | `needs_llm` | UT-REL-05 |
| EC-083 | "لأم ولد" vs "لأم" | Real: `b000349` "ابنا العباس لأم (٤) ولد" = mother was an umm walad, **not** maternal siblings. `b000360` "بنات العباس لأمهات أولاد". `b000488` "وأخواهما لأمهما", `b000502` "وأَخَوا عاصم لأمه" = maternal siblings. | Pattern distinguishes `لأم(هات)? (\(\S+\) )?ولد` / `أولاد` from `لأمه/لأمها/لأمهما` | `umm walad` → attribute `mother_status: umm_walad` on each child. `لأمه` → `sibling_of {kind: maternal}`. | — | UT-REL-06 |
| EC-084 | Inferred relation (not stated) | Real: "أولاد رسول الله" heading `b000104` + entry "١ - فاطمة." → `child_of` the Prophet | Relation derived from section context | `assertion: inferred`, `origin: ai_generated`, evidence anchors = the heading and the entry. | — | UT-REL-07 |
| EC-085 | Conflicting statements ("وقيل") | Real: `b000138` "وقيل: إنَّ اسم أبي هالة: هند بن زرارة" | Marker `وقيل` / `ويقال` | Store both as alternative values with `qualifier: reported_opinion`. Never pick one. | `metadata_conflict` | UT-REL-08 |

## J. LLM failures

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-090 | LLM invents a quote or a person | *hyp.* returns "هند بنت عتيق روت حديثًا" | `validation/evidence.py`: the quote is not found in the source block | Fact rejected (`evidence = 0`). Never stored as approved. Logged with the prompt version. | `evidence_not_found` | UT-EVD-02, LLM-FX-02 |
| EC-091 | LLM returns invalid JSON or a wrong schema | *hyp.* trailing text or missing field | Pydantic validation | One repair retry with the error message (`schema = 0.9`). If it fails again → `schema = 0`, item to review. | `schema_invalid` | LLM-FX-03 |
| EC-092 | Timeout or rate limit | *hyp.* HTTP 429 | Provider error | Exponential backoff (3 tries). Then mark the step `needs_llm`. Deterministic results still ship. | `needs_llm` | LLM-FX-04 |
| EC-093 | No API key / offline | Real: default MVP mode | `llm.provider = null` | `NullProvider` returns "not available". LLM-only tasks become `needs_llm` review items. The whole pipeline still runs. | `needs_llm` | INT-RUN-03 |
| EC-094 | Two models disagree | *hyp.* Model A: sibling kind `full`. Model B: `maternal`. | Field-level comparison in `consensus.py` | Judge model (a different family). If still unresolved → review with both outputs shown. The system never picks one silently. | `model_disagreement` | UT-CON-02 |
| EC-095 | Model output changes between runs | *hyp.* provider updates its model | Model ID + prompt version are in the cache key and the manifest | Temperature 0 + response cache gives the same output. A new model ID → new cache key → diff report. | — | INV-03 |
| EC-096 | Context too long | *hyp.* a 2,000-page book | Token estimate per call | Chunk by section/unit (never mid-entry). One unit + its footnotes per call. | — | UT-LLM-05 |

## K. Validation & review

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-100 | Sensitive content with high confidence | Real: `b000228` "وإسناده ضعيف" (hadith grading in an editor footnote) | `validation/sensitivity.py` categories (DECISIONS §8) | Always `pending_review`, whatever the score. | `sensitive_content` | UT-SEN-01 |
| EC-101 | Prophetic attribution | Real: 8 `c1` spans (Prophetic speech, inferred) | Span class `c1` or the pattern `قال رسول الله` | Category `prophetic_attribution` → always review. | `sensitive_content` | UT-SEN-02 |
| EC-102 | Reviewers disagree | *hyp.* reviewer A approves, B edits | Two decisions on one item | Second-level review (senior scholar role). Both decisions are kept in the audit trail. | — | UT-REV-03 |
| EC-103 | Reviewer edits a fact | *hyp.* corrects a gender | Review action `edited` | The edited value is stored with `origin: ai_generated` → `reviewed_by`. The original AI output is kept. The correction is exported to the training set. | — | UT-REV-04 |
| EC-104 | Review backlog grows too large | *hyp.* 10k pending items | Queue size metrics | Priority = sensitivity × (1 − confidence) × reach. Low-risk categories get batch approval of samples. Thresholds are calibrated. | — | UT-REV-05 |
| EC-105 | Confidence not calibrated | *hyp.* 0.9-scored items are only 70% correct | Calibration report on the reviewed sample | Adjust the factors and thresholds per category in config, never in code. | — | EV-03 |

## L. Scale & operations

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-110 | Very large book | *hyp.* 30 volumes, 10k pages | Page count | Process by section in parallel. Memory is streamed per page. Unit-level LLM batching. | — | PERF-01 |
| EC-111 | Thousands of books per month | *hyp.* 10k books | Throughput metrics | Production: Prefect workers scale horizontally. Batch LLM APIs. Cache. Open-weight models for bulk tasks. | — | design only |
| EC-112 | Cost runaway | *hyp.* hard-model escalation on every unit | Budget per book in the manifest | Router: rules → small model → large model. Escalate only on low confidence. Hard cap per book. | — | UT-LLM-06 |
| EC-113 | Config changed between runs | *hyp.* threshold 0.8 → 0.85 | `config_hash` in the manifest | Re-scoring only (no re-extraction). Diff report. | — | INV-04 |

## M. Publishing & search

| ID | Scenario | Example | Detection | Handling | Issue code | Test |
|---|---|---|---|---|---|---|
| EC-120 | Unapproved data must not be published | *hyp.* `pending_review` unit | Status filter | Publish/export only `auto_approved`, `approved` and `edited`. Others are visible only in review. | — | UT-PUB-01 |
| EC-121 | AI interpretation shown as author's statement | *hyp.* UI shows an inferred relation without a label | `origin` / `assertion` fields | Every published item carries `origin` + `assertion`. The UI labels `ai_generated` visibly. | — | UT-PUB-02 |
| EC-122 | Search by a spelling variant | Real: query "الاخوة" must find "الأُخوة" | Lexical index on the normalized copy | Both forms return the same results. Highlight uses the original offsets. | — | UT-SRC-02 |
| EC-123 | Stale anchor at publish time | *hyp.* source revised after approval | `block_hash` check at export | Item withheld from publishing until re-reviewed. | `anchor_stale` | UT-PUB-03 |

---

## Coverage of the required list

unknown schema_version EC-001 · new source format EC-002 · renamed/missing fields EC-003/004 · revision r7 EC-012 · block deleted EC-013 · offsets after normalization EC-015 · missing pages 1/2/4/18 EC-021 · PDF/JSON page mismatch EC-022/023 · TOC Shamela-key offset EC-024 · entries mid-sentence EC-031 · multiple entries per block EC-030 · editor lists EC-033 · continued footnotes EC-040 · nested footnote EC-042 · footnote without marker EC-041 · ref to missing block EC-044 · entry without footnote EC-034 · same-name persons EC-070 · ابن mid-chain EC-072 · Hind gender EC-071 · لأم ولد vs لأم EC-083 · dual ابنا EC-080/081/082 · honorifics EC-062 · diacritics EC-060 · spelling variants EC-061/027 · LLM invents quote EC-090 · invalid JSON EC-091 · timeout EC-092 · models disagree EC-094 · prompt injection EC-067 · sensitive EC-100/101 · reviewer disagreement EC-102 · duplicate runs EC-016 · partial failure EC-017 · very large book EC-110 · multi-volume EC-009 · non-Arabic EC-008 · scanned-only EC-007.
