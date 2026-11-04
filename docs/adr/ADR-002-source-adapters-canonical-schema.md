# ADR-002: Source adapters + versioned canonical schema

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

Books will come from more than one producer, and their formats will change over time. The sample already shows versioning on the source side: `revision.content.schema_version: "3.0"`, `revision.adapter_semver: "1.3.0"`, `pub.source_code: "src-shamela"`. The assignment also says OCR is handled by a separate team, so OCR output in another JSON format is expected in future.

Downstream code must not know about these source-specific quirks:
- TOC `source_page` is the Shamela page key (`content.pages[].source_ref.key`), not the printed page `n`. The offset between them changes along the book (2 → 3 → 4).
- Footnote continuation is marked with `continues: true` and no `marker` (16 blocks).
- `spans[].class` values `c1`, `c2`, `c4`, `c5` are undocumented.

## Decision

1. Define a **canonical schema** (`canonical/models.py`, `canonical_schema_version = "1.0"`): `CanonicalBook` → `pages[]` → `blocks[]` with `refs[]` and `spans[]` (see [03-data-contracts.md](../03-data-contracts.md)). Every downstream step reads only canonical objects.
2. Each source format gets one **adapter** implementing `SourceAdapter` (`adapters/base.py`): `adapter_id`, `adapter_version`, `can_handle(raw) -> bool`, `to_canonical(raw) -> CanonicalBook`.
3. A **registry** (`adapters/registry.py`) selects the adapter by the key `(source_code, schema_version)`. The MVP registers `("src-shamela", "3.0") -> ShamelaV3Adapter`.
4. **Fail closed:** an unknown key raises `UnknownSchemaVersion` and records issue `unknown_schema_version`. The pipeline never guesses.
5. **Nothing is lost:** fields the adapter does not map are kept verbatim in `raw_extras` (per book, page and block).
6. Adapters resolve source quirks. They expose `Page.source_key` so TOC entries can be aligned by key, normalize `continues`, and keep spans with their raw class names.
7. Each adapter ships **golden tests**: `tests/golden/<adapter_id>/input.json` → `expected_canonical.json`.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Adapter per (source, schema version) + canonical schema (chosen)** | New format = new adapter only; downstream untouched; explicit versions; testable with golden files | One more model layer to maintain |
| B. Process the Shamela JSON directly everywhere | Fastest for one book | Every processor knows Shamela quirks; a format change breaks all steps |
| C. Generic "auto-mapping" with an LLM | Handles unknown formats | Non-deterministic; silent structural errors; violates repeatability (ADR-011) |
| D. Convert everything to TEI XML | Rich standard | Heavy; lossy for our refs; no benefit now |

## Consequences

- **+** Adding a source (e.g. the OCR team's JSON) needs one adapter plus a golden test; tickets can be written in isolation.
- **+** Canonical schema changes are versioned, so old outputs stay interpretable.
- **−** Adapter authors must document every mapping decision in the adapter docstring.
- **−** Two schema versions may be live at once; the registry must support both.

## Compliance / how verified

- Golden test for `ShamelaV3Adapter` on the sample: 594 blocks; kinds text 260, footnote 317, heading 15, toc_heading 2; 300 refs.
- Test: the registry raises `UnknownSchemaVersion` for `("src-shamela", "4.0")` and records `unknown_schema_version`.
- Test: every top-level key of the input appears either mapped or in `raw_extras`.

## Related

ADR-003, ADR-011, ADR-017; Epic E01 tickets.
