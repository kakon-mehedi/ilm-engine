# ADR-003: Anchors — block ID + code-point offsets on original text

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

§6 requires that every extracted knowledge unit is traceable to its source. §2.F asks for "precise source location wherever possible".

The sample provides:
- Stable source block IDs (`b000135`) and page fields `n` and `scan_page`. `scan_page` equals the PDF page number (checked on page 25).
- Character offsets in `refs`. For example, `b000135` has refs `[0,3]→b000139`, `[25,28]→b000140`, `[66,69]→b000141` and `[98,101]→b000142`.
- No text layer in the PDF. Word-level positions on the scan (bounding boxes) are therefore unavailable, but page-level linking to the scan works.

A tempting assumption is that only block-level traceability is possible because not all blocks carry offsets. That is not the case: every block has `text`, so the offsets of any quote can be computed. The real limit is the PDF, not the JSON.

## Decision

An **Anchor** is:

```json
{"pub_ref": "pub_01M0CJECV4ZHFTP02BJQ6D3STJ@r6", "page": 25, "scan_page": 25,
 "block_id": "b000135", "start": 60, "end": 65, "quote": "أسلمت",
 "block_hash": "sha256:56770406fa03b53a0b19d3e6e3bc9d3f604f79ae0e8e8a7da3eaeb399a3ff989"}
```

- Offsets are Python `str` indices (Unicode code points) into the **original, un-normalized** block text. `end` is exclusive.
- Invariant: `block.text[start:end] == quote`.
- A whole-block anchor uses `start = 0, end = len(text)`. Its `quote` may be truncated to 120 characters, with `quote_truncated: true`.
- Evidence that spans several blocks uses a list of anchors (e.g. an entry plus its footnote).
- Visual link: `scan_page` → PDF page. Future OCR sources may add an optional `bbox`. The field is reserved but unused in the MVP.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. block_id + code-point offsets + quote + block_hash (chosen)** | Precise; verifiable; survives display changes; detects source drift | Offsets depend on exact text; any source edit invalidates them (handled by ADR-017) |
| B. Block-level only | Simple | Not "precise"; cannot show which words support a fact |
| C. Offsets on normalized text | Robust to diacritic differences | Offsets do not map back to the original, which breaks §6 traceability |
| D. Byte offsets (UTF-8) | Language-neutral | Arabic characters are multi-byte; error-prone for humans and for Python slicing |
| E. W3C TextQuoteSelector only (prefix/exact/suffix) | Robust to small edits | Ambiguous for repeated phrases; slower lookup; can be added later |

## Consequences

- **+** Every claim can be shown in context and checked automatically.
- **+** Anchors are also the evidence used by the hallucination guard (ADR-007).
- **−** Anchors become stale when source text changes. ADR-017 defines how that is detected.
- **−** A UI must slice by code points, not by bytes or grapheme clusters.

## Compliance / how verified

- Unit test on the sample: `b000135` has length 102; `أسلمت` is at 60–65, `وتزوجت` at 70–76, and `ولم يُروَ عنها شيءٌ` at 78–97.
- Property test: for every anchor in every output file, `text[start:end] == quote` and `block_hash` matches.
- Test: refs from the adapter become anchors whose quotes equal the marker text (e.g. `(١)` at 25–28).

## Related

ADR-001, ADR-007, ADR-010, ADR-017.
