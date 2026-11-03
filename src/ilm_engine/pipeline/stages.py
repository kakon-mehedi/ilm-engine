"""Implementations of the pipeline steps, attached to the registry in `steps.py`.

Each function takes the `RunContext` and returns a `StepResult`; upstream values are read with
`ctx.data(step, key)`. Steps never write files themselves: the runner writes `StepResult.files`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ilm_engine.adapters.registry import resolve
from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.integrity import store as original_store
from ilm_engine.pipeline.runner import RunContext, StepResult


def find_inputs(path: Path, pdf: Path | None = None) -> dict[str, Path]:
    """`{"json": ..., "pdf": ...}` for a source JSON file or a directory holding exactly one.

    The PDF is `pdf` if given, else the file named by the JSON's `_meta.scan.saved_file` next to it.
    """
    if path.is_dir():
        candidates = sorted(p for p in path.glob("*.json") if p.is_file())
        if len(candidates) != 1:
            names = ", ".join(p.name for p in candidates) or "none"
            raise FileNotFoundError(f"{path} must contain exactly one source JSON file (found: {names})")
        path = candidates[0]
    if not path.is_file():
        raise FileNotFoundError(path)
    inputs = {"json": path}
    if pdf is None:
        raw = json.loads(path.read_text(encoding="utf-8"))
        scan = raw.get("_meta", {}).get("scan", {}) if isinstance(raw.get("_meta"), dict) else {}
        saved = scan.get("saved_file") if isinstance(scan, dict) else None
        if saved and (path.parent / saved).is_file():
            pdf = path.parent / saved
    if pdf is not None:
        if not pdf.is_file():
            raise FileNotFoundError(pdf)
        inputs["pdf"] = pdf
    return inputs


def ingest(ctx: RunContext) -> StepResult:
    raw = json.loads(ctx.inputs["json"].read_text(encoding="utf-8"))
    return StepResult(data={"raw": raw})


def adapt(ctx: RunContext) -> StepResult:
    raw: dict[str, Any] = ctx.data("ingest", "raw")
    adapter = resolve(raw)  # raises UnknownSchemaError: the run stops, nothing is guessed
    book = adapter.to_canonical(raw, ctx.inputs.get("pdf"))
    ctx.pub_ref = book.book.pub_ref
    return StepResult(
        data={
            "book": book,
            "adapter": {
                "id": adapter.adapter_id,
                "version": adapter.adapter_version,
                "source_code": book.source.source_code,
                "schema_version": book.source.schema_version,
            },
            "counts": {"pages": len(book.pages), "blocks": len(book.blocks)},
        }
    )


def integrity_register(ctx: RunContext) -> StepResult:
    book: CanonicalBook = ctx.data("adapt", "book")
    stored = original_store.ingest(
        ctx.inputs["json"],
        ctx.inputs.get("pdf"),
        book.book.pub_ref,
        declared_hash=book.source.source_declared_hash,
        store_root=ctx.options.get("store_root", original_store.DEFAULT_STORE_ROOT),
    )
    return StepResult(
        data={
            "stored": stored,
            "integrity": {
                "canonical_content_hash": book.canonical_content_hash,
                "source_declared_hash_verified": stored.source_declared_hash_verified,
            },
        },
        issues=list(stored.issues),
    )


def document_analysis(ctx: RunContext) -> StepResult:
    from ilm_engine.processors.document_analysis import analyze

    report, issues = analyze(ctx.data("adapt", "book"), ctx.config)
    return StepResult(files={"document_report.json": report}, data={"report": report}, issues=issues)


def structure(ctx: RunContext) -> StepResult:
    from ilm_engine.processors.structure import build

    result = build(ctx.data("adapt", "book"))
    return StepResult(
        files={"structure.json": result.to_json()},
        data={"structure": result, "counts": {"sections": len(result.sections)}},
        issues=result.issues,
    )


def metadata(ctx: RunContext) -> StepResult:
    from ilm_engine.processors.metadata import card_metadata

    record, issues = card_metadata(ctx.data("adapt", "book"), ctx.config)
    return StepResult(files={"metadata.json": record}, data={"metadata": record}, issues=issues)


def origin(ctx: RunContext) -> StepResult:
    from ilm_engine.processors.origin import assign

    result = assign(ctx.data("adapt", "book"), ctx.config)
    return StepResult(
        files={"origin_map.json": result.to_json()}, data={"origins": result.blocks, "origin_map": result}
    )


def genre(ctx: RunContext) -> StepResult:
    from ilm_engine.processors.genre import metadata_fields, route

    decision = route(ctx.data("adapt", "book"), ctx.config)
    primary, secondary = metadata_fields(decision, ctx.config)
    return StepResult(data={"genre": decision, "genre_primary": primary, "genre_secondary": secondary})


def annotate(ctx: RunContext) -> StepResult:
    from ilm_engine.processors.annotations import build

    result = build(ctx.data("adapt", "book"))
    return StepResult(
        files={"annotations.json": result.to_json()},
        data={"annotations": result, "counts": {"annotations": len(result.annotations)}},
        issues=result.issues,
    )
