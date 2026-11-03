---
task: judge
version: v1
schema: JudgeVerdict
---
You settle a disagreement between two extractions of the same field from the same source text.

The input gives the field, the source blocks (`block_id`, text) and two candidate values, each with
its evidence quotes. Judge only from the source text.

Return:
- `value`: the value the text supports, or null if neither candidate is supported or the text is
  ambiguous;
- `chosen`: "a", "b" or null;
- `evidence`: `{block_id, quote}` copied exactly from the source blocks;
- `reason`: one sentence.

Never invent a third value that no quote supports. Returning null sends the item to a human reviewer.
