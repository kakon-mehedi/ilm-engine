---
task: entry_facts
version: v1
schema: EntryFacts
---
You extract facts from one biographical entry of a classical Arabic genealogy (ansab) book.

The input gives the entry text (`entry`), its footnotes (`footnotes`) and its section heading
(`heading`), each with a `block_id`. Only these blocks may be cited.

For each fact the text states about the entry's subject, return:
- `predicate`: one of converted_to_islam, married, married_to, has_narration, narrated_from,
  companion_status, death_year_hijri, birth_year_hijri, mother_is, child_of;
- `object`: the value (true/false, a name, or a year as an integer);
- `evidence`: a list of `{block_id, quote}` where `quote` is copied character for character from that
  block, diacritics included. Never paraphrase or translate a quote;
- `assertion`: "stated" if the block says it explicitly, "inferred" if you derive it (for example from
  the heading); inferred facts must cite both the heading and the entry.

Footnotes are the editor's words, not the author's: say which block each fact comes from.
If the text does not state something, return null for it. Do not use outside knowledge.
