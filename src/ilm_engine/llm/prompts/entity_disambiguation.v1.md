---
task: entity_disambiguation
version: v1
schema: EntityDisambiguation
---
You decide whether a name mention refers to one of the candidate persons.

The input gives the mention (`block_id`, `quote`, surrounding text), and candidates with their
nasab chain, gender, entry number and section. Names repeat across different people (for example
"هند" is both هند بنت عتيق, female, and هند بن أبي هالة, male), so decide only from the given text.

Return:
- `entity_id`: the matching candidate, or null if none matches or the text cannot decide;
- `gender`: "m", "f" or "unknown", from grammar in the text (dual and plural forms such as "ابنا"
  are masculine);
- `evidence`: `{block_id, quote}` pairs copied exactly that support the decision.

Return null rather than picking among equally possible candidates.
