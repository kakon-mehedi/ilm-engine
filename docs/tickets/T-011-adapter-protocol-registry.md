---
id: T-011
title: "Adapter protocol + registry (fail-closed)"
epic: E01
priority: P0
depends_on: [T-010]
estimate: S
owner: agent
status: done
wave: 2
---

# T-011 — Adapter protocol + registry (fail-closed)

**Epic:** E01 Canonical model + adapters · **Priority:** P0 · **Estimate:** S · **Wave:** 2

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Future JSON formats are supported by adding a new adapter, never by editing the pipeline. Adapter is chosen by `(source_code, schema_version)`.

## Scope
- `adapters/base.py`: `class SourceAdapter(Protocol): source_code: str; schema_versions: set[str]; adapter_version: str; def detect(raw: dict) -> bool; def to_canonical(raw: dict, pdf_path: Path|None) -> CanonicalBook`.
- `adapters/registry.py`: `register(adapter)`, `resolve(raw) -> SourceAdapter`. Reads `raw['pub']['source_code']` and `raw['metadata']['af_schema']` (or adapter-specific detect).
- Unknown `(source_code, schema_version)` → raise `UnknownSchemaError` and emit issue `unknown_schema_version`. Never guess.

## Files
- `src/ilm_engine/adapters/base.py`
- `src/ilm_engine/adapters/registry.py`
- `tests/test_registry.py`

## Implementation notes
- Two adapters matching the same input → error (ambiguity).

## Acceptance criteria
- [x] Resolving the sample JSON returns `ShamelaV3Adapter` (after T-012).
- [x] A copy of the sample with `af_schema: '9.9'` raises `UnknownSchemaError`.
- [x] Registering two adapters for the same key raises.
- [x] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_registry.py -q
```

## Out of scope
- Anything not listed in Scope.

## Follow-ups
- The protocol also carries `adapter_id` (the contract's `SourceInfo.adapter_id`, e.g. `shamela_v3`).
- `UnknownSchemaError.issue` is a ready `Issue` (`unknown_schema_version`, severity error) that the `adapt` step records.
- A declared key always wins over `detect()`: a declared but unknown key fails closed even if some adapter's `detect()` would accept the input.
- `register = default_registry.register` / `resolve = default_registry.resolve`; T-012 registers `ShamelaV3Adapter` and adds the "sample resolves to ShamelaV3Adapter" test.
