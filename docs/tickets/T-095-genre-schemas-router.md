---
id: T-095
title: "Genre plugin schemas (7) + genre router"
epic: E09
priority: P0
depends_on: [T-040, T-010]
estimate: M
owner: agent
status: todo
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
- [ ] Sample → primary biography/ansab, secondary includes hadith.
- [ ] All 7 schemas importable and listed by `genres.registry()`.
- [ ] Footnote b000228 ('وإسناده ضعيف') parses into hadith schema with grading 'ضعيف' flagged sensitive.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_genre.py -q
```

## Out of scope
- LLM genre classification (optional via prompt genre_classify.v1).
