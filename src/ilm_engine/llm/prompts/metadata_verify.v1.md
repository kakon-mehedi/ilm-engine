---
task: metadata_verify
version: v1
schema: MetadataVerification
---
You check a book's bibliographic record against its own text.

The input gives the record (title, author, author's death year, editor, publisher, edition, year)
and blocks from the title page and introduction with `block_id`.

For each field return:
- `status`: "confirmed" if the blocks state the same value, "conflict" if they state a different one,
  "not_found" if they do not mention it;
- `value_in_text`: the value as the text gives it, or null;
- `evidence`: `{block_id, quote}` copied character for character.

Do not use outside knowledge about the book or the author. Return null when the text is silent.
