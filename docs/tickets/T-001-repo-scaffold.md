---
id: T-001
title: "Repository scaffold (uv, pyproject, ruff, pytest)"
epic: E00
priority: P0
depends_on: []
estimate: S
owner: agent
status: todo
wave: 0
---

# T-001 — Repository scaffold (uv, pyproject, ruff, pytest)

**Epic:** E00 Setup · **Priority:** P0 · **Estimate:** S · **Wave:** 0

> Before starting: read `docs/DECISIONS.md` (names, paths, IDs, anchors, issue codes are binding) and the tickets listed in `depends_on`.

## Context
Create the MVP Python project exactly as laid out in DECISIONS.md §3 so every later ticket has a place to put code.

## Scope
- The repository already exists (`ilm-engine`, branch `main`). `data/` is git-ignored and read-only: never commit or modify it.
- Create `pyproject.toml` at the repository root (Python 3.12, src layout, package `ilm_engine`, console script `ilm-engine = ilm_engine.cli:app`).
- Runtime deps: `pydantic>=2`, `typer`, `pyyaml`. Dev deps: `pytest`, `ruff`, `mypy`. Optional extras: `llm` (`anthropic`, `litellm`), `nlp` (`camel-tools`), `semantic` (`sentence-transformers`).
- Create every package directory from DECISIONS §3 with empty `__init__.py` files.
- `.gitignore` ignores `output/`, `store/`, `.cache/`, `.venv/`.
- A placeholder `cli.py` with a typer `app` and a `version` command.

## Files
- `pyproject.toml`
- `.gitignore`
- `src/ilm_engine/**/__init__.py`
- `src/ilm_engine/cli.py`
- `tests/test_smoke.py`

## Implementation notes
- Do not add Celery/Redis (ADR-004).
- ruff config: line-length 110, target py312, select E,F,I,B,UP.

## Acceptance criteria
- [ ] `uv sync` succeeds.
- [ ] `uv run ilm-engine version` prints the package version.
- [ ] `uv run pytest` runs and `test_smoke.py` passes.
- [ ] `uv run ruff check .` is clean.
- [ ] Directory tree matches DECISIONS §3 (all sub-packages exist).
- [ ] Definition of Done (BOARD.md) satisfied.

## Test commands
```bash
uv sync && uv run pytest -q && uv run ruff check .
```

## Out of scope
- Any business logic.
