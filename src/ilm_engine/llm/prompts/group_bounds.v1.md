---
task: group_bounds
version: v1
schema: GroupBounds
---
You decide which consecutive biographical entries form one sibling group in a classical Arabic
genealogy book.

The author closes a group of siblings with a phrase such as "ابنا فلان" (two sons of), "بنو فلان"
(children of), "بنات فلان" (daughters of) or "أمهم فلانة" (their mother). The input lists entries with
`entry_no`, `block_id` and text, and the candidate closing phrase.

Return:
- `entry_nos`: the entries the closing phrase covers (a dual form such as "ابنا" covers exactly two);
- `parent`: the parent named by the phrase, or null;
- `kind`: "full", "paternal", "maternal" or "unknown". "لأم ولد" means the mother was an umm walad
  (a concubine); it is NOT a maternal-sibling relation;
- `evidence`: `{block_id, quote}` with the closing phrase copied exactly.

If the text does not settle the group, return null for the uncertain field. Do not guess.
