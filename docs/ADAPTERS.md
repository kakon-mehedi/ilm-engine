# Writing a source adapter

A source adapter turns one input format into the canonical book (`canonical/models.py`,
[03-data-contracts.md](03-data-contracts.md) §2). Supporting a new archive, export version or OCR
format means **adding an adapter**; the pipeline itself is never edited (ADR-002). Two adapters ship
with the MVP:

| Adapter | `source_code` | Schema versions | Resolved by |
|---|---|---|---|
| `adapters/shamela_v3.py` | `src-shamela` | `3.0` | declared key (`pub.source_code`, `metadata.af_schema`) |
| `adapters/ocr_team_v1.py` (example) | `src-ocr-team` | `1.0` | `detect()` (the format declares no key) |

## 1. Decide how the format is recognized

The registry (`adapters/registry.py`) resolves an input in this order:

1. **Declared key.** If the JSON has `pub.source_code` and `metadata.af_schema`, exactly that
   `(source_code, schema_version)` must be registered. An unknown key fails closed with
   `UnknownSchemaError` (issue `unknown_schema_version`, CLI exit code 2), even if another adapter's
   `detect()` would accept the input. Nothing is guessed.
2. **Detection.** Without a declared key, every adapter's `detect(raw)` is asked. Exactly one must
   answer `True`; two answers raise `AmbiguousAdapterError`, none raises `UnknownSchemaError`.

Keep `detect()` strict: check a format marker and the major version, not the presence of common keys.

## 2. Implement the protocol

```python
class MyFormatV1Adapter:
    adapter_id = "my_format_v1"          # recorded in SourceInfo and the run manifest
    source_code = "src-my-format"
    schema_versions = frozenset({"1.0"})  # source versions this adapter reads
    adapter_version = "1.0.0"             # our adapter's own version (see §5)

    def detect(self, raw: dict) -> bool: ...
    def to_canonical(self, raw: dict, pdf_path: Path | None = None) -> CanonicalBook: ...
```

Mapping rules (enforced by the canonical models or the tests):

- **Text is copied verbatim.** No normalization, trimming or re-encoding; `block_hash` is computed
  with `integrity.hashing.block_hash(text)` and `canonical_content_hash` with `content_hash(blocks)`.
- **Keep source IDs.** `block_id` is the source's block or line ID; never renumber. `order` is the
  global reading order `0..N-1`.
- **Pages:** `n` is the printed page number, `scan_page` the PDF page, `source_key` the source's own
  page key (TOC alignment uses it).
- **Offsets** of refs and spans are code-point indices into the original text (`end` exclusive) and
  must lie inside the block; span `text` must equal the slice.
- **Nothing is lost.** Every source field you do not map goes into `raw_extras` (book, page or block
  level), verbatim. Fields such as OCR bounding boxes stay there until a canonical field is approved
  in an ADR.
- **Fail closed.** A missing required field raises `SourceFormatError` with its JSON path (issue
  `schema_invalid`); do not fill in defaults that hide a broken input.
- **Do not mutate `raw`** and do not parse the PDF beyond what you need for references.

## 3. Register it

Call `register(MyFormatV1Adapter())` at the end of the module and import the module in
`adapters/__init__.py`. Registering two adapters for the same `(source_code, schema_version)` raises
`DuplicateAdapterError`.

## 4. Add a golden test

1. Put a small input in `tests/golden/<adapter_id>/input.json` (a few pages that exercise headings,
   footnotes, refs and spans). Use synthetic text unless the source may be redistributed; excerpts of
   confidential books are generated locally and git-ignored (see `tests/golden/shamela_v3/`).
2. Generate `expected_canonical.json` with `storage.json_store.dumps(adapter.to_canonical(raw))` and
   review it line by line.
3. Test byte equality and print `tools.update_golden.readable_diff` on mismatch
   (`tests/test_ocr_team_v1.py` is the template). Also test `resolve()` picks your adapter and that
   the structural steps (`document_analysis`, `structure`, `origin`) run on the sample.

## 5. Version bumps

| Change | What to do |
|---|---|
| The source publishes a new schema version with the same shape | Add it to `schema_versions`, add a golden case |
| The source changes shape | New adapter module (`<source>_v<N>.py`) with its own goldens; keep the old one |
| Our mapping changes the canonical output | Bump `adapter_version`, regenerate and review the goldens in the same commit (EC-006) |
| Bug fix with no output change | Patch version bump; goldens must stay identical |

The adapter ID and version are recorded in every `run_manifest.json`, so outputs stay traceable to
the mapping that produced them.
