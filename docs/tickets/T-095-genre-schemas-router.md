---
id: T-095
title: "Genre plugin schemas (7) + genre router"
epic: E09
priority: P0
depends_on: [T-040, T-010]
estimate: M
owner: agent
status: done
wave: 5
---

# T-095 — Genre plugin schemas (7) + genre router

**Epic:** E09 LLM gateway & genre extraction · **Priority:** P0 · **Estimate:** M · **Wave:** 5

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Requirement F: dynamic extraction per genre. Adding a genre = adding a plugin, no pipeline change.

## Scope
- `extractors/genres/<genre>.py` each exposing `GENRE`, Pydantic `UnitSchema`, `sensitive_fields`, `prompt_task`: fiqh{masala, hukm, dalil[], madhhab, qail, khilaf[]}, hadith{matn, isnad[rawi], takhrij[], grading, sharh_ref}, tafsir{ayah_ref, tafsir_text, aqwal[], mufassir}, seerah{event, date_hijri, place, persons[]}, aqeedah{concept, proposition, evidence[]}, history{event, date, place, persons[]}, biography{person, nasab, kunya, laqab, birth, death, teachers[], students[], relatives[]}.
- `processors/genre.py` router: category map ('الأنساب' → biography/ansab) + content signals (takhrij patterns 'رواه … رقم' → secondary hadith); output `{primary, secondary[], signals, confidence}`.

## Files
- `src/ilm_engine/extractors/genres/*.py`
- `src/ilm_engine/processors/genre.py`
- `tests/test_genre.py`

## Implementation notes
- Sensitive fields: hadith.grading, fiqh.hukm, aqeedah.proposition.

## Acceptance criteria
- [x] Sample → primary biography/ansab, secondary includes hadith.
- [x] All 7 schemas importable and listed by `genres.registry()`.
- [x] Footnote b000228 ('وإسناده ضعيف') parses into hadith schema with grading 'ضعيف' flagged sensitive.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_genre.py -q
```

## Out of scope
- LLM genre classification (optional via prompt genre_classify.v1).

## Follow-ups
- Plugins are single modules `extractors/genres/<genre>.py` (`GENRE`, `SUB_TYPES`, `UNIT_TYPES`, `UnitSchema`, `sensitive_fields`, `prompt_task`); `genres.registry()` lists all 7. Sensitive payload fields carry `json_schema_extra={"sensitive": True, "sensitive_category": …}`: hadith.grading (hadith_grading), hadith.matn (prophetic_attribution), fiqh.hukm (fiqh_ruling), aqeedah.proposition (aqeedah_proposition).
- Hadith (MVP candidate parser): `parse_takhrij(text)` extracts collector references `رواه X في "Y" (v/ p) (رقم: n)` and the grading statement; b000228 → grading `ضعيف` / `daif`, reason "لكثرة المجاهيل", sensitive `hadith_grading`, refs الطبراني الكبير 3/166 #3258 and أسد الغابة 2/55.
- Router: category prior (`الأنساب` → biography/ansab, confidence 0.95) + content signals with up to 3 anchored examples per genre; a genre becomes secondary with ≥ 3 signal matches. Without a category the strongest content genre becomes primary at LLM-level confidence (0.75 → review). The optional LLM confirmation (`genre_classify` prompt) is not wired; the category prior settles the sample.
- Only `biography` has a prompt (`entry_facts`); the other genres name `extract_<genre>` tasks whose prompts are added with their extractors.
- The genre step fills `genre_primary` / `genre_secondary` metadata fields (inferred, ai_generated) in its step data; `export` merges them into `metadata`. `schemas/` now also holds `genre_<genre>.json`.
