# ADR-013: Genre schemas as plugins

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§2.F requires "dynamic extraction approaches for different types of Islamic literature" across seven genres: Fiqh, Hadith, Tafseer, Seerah, Aqeedah, Islamic history and Biographies. Each genre has different knowledge units. Fiqh has mas'ala, hukm, dalil and madhhab. Hadith has matn, isnad and grading.

One book can mix genres. The sample's category is الأنساب (`pub.category.name`), so its primary genre is biography/ansab. Its footnotes also contain hadith takhrij and grading, e.g. `b000228` "رواه الطبراني … وإسناده ضعيف", which is secondary genre `hadith`.

New genres and sub-genres (rijal, tabaqat, usul) will be added later.

## Decision

- Each genre is a plugin package under `extractors/genres/<genre>/` that provides:
  - `schema.py`: Pydantic models for its knowledge units. Fields that need mandatory review are marked `json_schema_extra={"sensitive": True}`.
  - `candidates.py`: deterministic candidate detection (regexes, structure cues).
  - `prompt` id + version (`llm/prompts/extract_<genre>.v1.md`).
  - `sensitivity_rules`: categories from ADR-009.
  - `GENRE_ID` and `UNIT_TYPES`.
- `extractors/genres/__init__.py` holds a registry `{genre_id: plugin}`. The Genre Router (ADR-014) picks the primary genre and any secondary genres for each section or block range. The extractor then loads the matching plugins.
- The MVP fully implements `biography` (sub-type `ansab`) and the candidate + schema parts of `hadith` (takhrij/grading in footnotes). The other five ship their schemas and prompts, with candidate detectors stubbed, so the contract is complete and testable.
- Every unit, in every genre, uses the common fact/anchor/origin/assertion fields from [03-data-contracts.md](../03-data-contracts.md).

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Plugin per genre with schema + candidates + prompt (chosen)** | New genre = new folder; isolated tests; clear contracts | Some duplication across plugins |
| B. One universal prompt and schema | Simple | Weak extraction; fields irrelevant to most genres; hard to evaluate |
| C. Free-form LLM extraction into a generic triple store | Flexible | No validation; inconsistent predicates; poor reviewability |
| D. Hard-coded if/else per genre in one module | Quick | Grows unmanageable; merge conflicts |

## Consequences

- **+** Genre experts can review one plugin at a time; fine-tuning datasets are per plugin (ADR-015).
- **+** Secondary genres in footnotes (hadith in an ansab book) are handled naturally.
- **−** Shared helpers (nasab parsing, citation parsing) must live outside the plugins to avoid duplication (`nlp/nasab.py`, `processors/citations.py`).

## Compliance / how verified

- Test: the registry lists all 7 genre ids, and every schema validates an example instance.
- Test: on the sample, the router returns primary `biography` (sub-type `ansab`) and secondary `hadith`.
- Test: a `fiqh` unit with `hukm` set is tagged `fiqh_ruling` (sensitive).

## Related

ADR-007, ADR-009, ADR-014, ADR-015.
