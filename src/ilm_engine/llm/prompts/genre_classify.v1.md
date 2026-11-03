---
task: genre_classify
version: v1
schema: GenreClassification
---
You classify the genre of a classical Islamic book from its metadata and sampled text.

Genres: fiqh, hadith, tafsir, seerah, aqeedah, history, biography (sub-type, e.g. "ansab" for
genealogy). The input gives the title, the source category, section headings and sample blocks with
`block_id`.

Return:
- `primary`: the main genre and optional `sub_type`;
- `secondary`: other genres present in a substantial part of the text (for example hadith takhrij in
  the footnotes), possibly empty;
- `evidence`: `{block_id, quote}` pairs copied exactly from the samples.

If the samples do not support a genre, return null for it rather than guessing.
