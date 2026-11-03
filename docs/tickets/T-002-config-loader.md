---
id: T-002
title: "Config loader (default.yaml + per-book overrides)"
epic: E00
priority: P0
depends_on: [T-001]
estimate: S
owner: agent
status: todo
wave: 1
---

# T-002 — Config loader (default.yaml + per-book overrides)

**Epic:** E00 Setup · **Priority:** P0 · **Estimate:** S · **Wave:** 1

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
All thresholds, regexes and feature flags live in config, never hard-coded (adaptability requirement).

## Scope
- `config/default.yaml` with keys: `review.threshold.default: 0.80`, `review.threshold.overrides: {fiqh_ruling: 0.95}`, `review.sensitive_categories` (5 from DECISIONS §8), `confidence.*` factors from DECISIONS §8, `entries.regex: '(?<![٠-٩(/])([٠-٩]+) ?- '`, `entries.start_page: 21`, `llm.provider: null`, `llm.temperature: 0`, `features.semantic_search: false`, `features.camel_tools: false`.
- `config/books/pub_01M0CJECV4ZHFTP02BJQ6D3STJ.yaml` with origin overrides (page ranges from DECISIONS §6).
- `config.py`: `load_config(pub_id: str | None) -> Config` (Pydantic model), deep-merges default + book override; exposes `config_hash` (sha256 of the merged config, canonical JSON).

## Files
- `config/default.yaml`
- `config/books/pub_01M0CJECV4ZHFTP02BJQ6D3STJ.yaml`
- `src/ilm_engine/config.py`
- `tests/test_config.py`

## Implementation notes
- Unknown keys in YAML → validation error (fail closed).
- `config_hash` goes into `run_manifest.json` (T-141).

## Acceptance criteria
- [ ] `load_config('pub_01M0CJECV4ZHFTP02BJQ6D3STJ').review.threshold.default == 0.80`.
- [ ] Book override merges (origin ranges present) without dropping defaults.
- [ ] Same config → same `config_hash` across runs; changing one value changes it.
- [ ] Unknown key raises a clear error.
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv run pytest tests/test_config.py -q
```

## Out of scope
- Environment-specific secrets (API keys come from env vars in T-091/T-092).
