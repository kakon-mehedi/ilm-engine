# ADR-018: Book family / related-works model

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§2.B requires identifying original/fundamental books and related works, mapping relationships such as Sharh, Hashiyah, translation, summary and explanation, and mapping corresponding sections across books. §2.G requires connecting knowledge across books. Step 4 of the data flow is "Identify book genre and related works".

This requirement is easy to under-specify. With a single sample book we cannot demonstrate Sharh↔Matn alignment. The sample is still rich in related-work signals:
- **Cited works with locators in footnotes:** الإصابة 145 times, أسد الغابة 67, السير 59, الطبقات الكبرى 45, التهذيب 32, الاستيعاب 31. Example: `b000139` "قال الحافظ في "الإصابة" (٨/ ١٥٧)" (volume 8, page 157).
- **Same-topic works named by the editor** in `b000018`: "الأُخوة الذين رُويَ عنهم الحديث" لأبي داود السِّجِسْتاني (offsets 151–182) and "تسمية من رُويَ عنه من أولاد العشرة" (216–250), plus his combined edition "الرّواة من الأُخوة والأخوات".
- **Another work by the same author:** `b000215` "انظر "المؤتلف" (٣/ ١٢٤٢) للمصنّف" (al-Daraqutni's al-Mu'talif wa al-Mukhtalif).
- **Internal references:** `b000063` "ترجمة رقم (٣٣)" (p. 11, offset 60) points to entry 33 of this book.
- **Edition relation:** the record itself is an edition (`editions[0]`, Dar al-Raya 1413/1993, tahqiq by Basim al-Jawabira) of work `wrk_01M0CJEXJ1ZJM9AEM1GYTHTYZE`.

## Decision

- **Entities:**
  - `Work` (abstract work, e.g. al-Isaba);
  - `Edition` (a concrete printing with tahqiq, publisher, year);
  - `Publication` (the archive record, `pub_…@r6`).
  Work IDs we create are `wrk_<12 hex>`. Source work IDs are kept as `source_work_id`.
- **Work relations** (DECISIONS.md §11): `sharh_of`, `hashiyah_of`, `mukhtasar_of`, `translation_of`, `edition_of`, `tahqiq_of`, `cites`, `same_topic_as`. Each relation carries evidence anchors, origin, assertion and confidence, exactly like person relations.
- **Pipeline:**
  1. `citations` (deterministic): parse quoted titles followed by locators `(vol/ page)`, `(ص: n)`, `(رقم: n)`, and normalize titles (ADR-012). Output `Citation` records with anchors. Internal references (`ترجمة رقم (n)`, `كما سيأتي`) become `InternalRef` records, resolved to entry units, or flagged `unresolved_internal_ref`.
  2. `related_works` (agentic in production; rules + alias table in the MVP): the Related-Works Resolver (ADR-014) maps cited titles to `Work` records using an alias table (`config/works_aliases.yaml`, e.g. "الإصابة" → "الإصابة في تمييز الصحابة", Ibn Hajar). It creates `cites` edges from this publication. Unmatched titles become `Work` stubs with `needs_review`.
  3. Same-topic signals in prefaces become `same_topic_as` (assertion `stated` when the editor says so, as in `b000018`).
- **Cross-book section mapping** (production, design only): for `sharh_of` and `hashiyah_of` pairs, align commentary segments to matn segments. Alignment uses quoted matn lemmas (the commentary usually quotes the matn, often in markup like "قوله: …"), embedding similarity (BGE-M3) and order constraints (monotonic alignment). Results are `SegmentAlignment` records with anchors on both books, and are reviewed.
- **Locators** are kept structured (`volume`, `page`, `number`), so links can later resolve to the cited book's own pages once that book is in the library.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Work/Edition/Publication model + typed work relations + citation parsing (chosen)** | Covers §2.B and §2.G; demonstrable on the sample; extensible to Sharh alignment | Alias table must be curated |
| B. Only free-text "related books" list | Easy | Not machine-usable; no relation types |
| C. Embedding similarity between whole books | Finds same-topic books | Cannot tell sharh from citation; no section mapping |
| D. Depend on an external catalog (e.g. OpenITI) only | Rich IDs | External dependency; still needs local parsing of citations |

## Consequences

- **+** The MVP demonstrates related works concretely: a cited-works graph with hundreds of edges and the editor's same-topic works.
- **+** The same model supports future Sharh/Hashiyah alignment without schema changes.
- **−** Title normalization has edge cases: "الطبقات" vs "الطبقات الكبرى", and the quoting typo in `b000143` (""والتهذيب""). These go through the alias table and review.

## Compliance / how verified

- Test: `b000139` yields a `Citation` with title "الإصابة", volume 8, page 157, and an anchor on the title.
- Test: `b000018` yields two `same_topic_as` relations with `assertion: stated` and `origin: editor_text`.
- Test: `b000063` yields an `InternalRef` resolved to the unit for entry 33.
- Count test: citation counts per normalized title are within ±5% of the reference counts in DECISIONS.md §7, because the counting method differs.

## Related

ADR-005, ADR-007, ADR-013, ADR-014.
