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
    from ilm_engine.processors.metadata import card_metadata, content_metadata, metadata_conflicts

    book = ctx.data("adapt", "book")
    record, issues = card_metadata(book, ctx.config)
    record, findings, more = content_metadata(
        book,
        record,
        ctx.data("origin", "origins"),
        ctx.data("structure", "structure"),
        ctx.config,
        llm_available=ctx.options.get("llm", "null") not in ("null",),
    )
    record, conflicts = metadata_conflicts(book, record, findings)
    return StepResult(
        files={"metadata.json": record},
        data={"metadata": record, "findings": findings},
        issues=[*issues, *more, *conflicts],
    )


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


def citations(ctx: RunContext) -> StepResult:
    from ilm_engine.extractors.units import detect_entries, unit_id
    from ilm_engine.processors.citations import extract, internal_refs

    book, origins = ctx.data("adapt", "book"), ctx.data("origin", "origins")
    result = extract(book, origins, ctx.config)
    entries = detect_entries(book, origins, ctx.config).entries
    refs = internal_refs(book, {entry.entry_no: unit_id(book.book.pub_ref, entry) for entry in entries})
    return StepResult(
        files={"citations.json": {**result.to_json(), "internal_refs": refs.refs}},
        data={
            "citations": result,
            "internal_refs": refs,
            "counts": {"citations": len(result.citations), "internal_refs": len(refs.refs)},
        },
        issues=[*result.issues, *refs.issues],
    )


def related_works(ctx: RunContext) -> StepResult:
    from ilm_engine.extractors.related_works import related_works as resolve_related

    result = resolve_related(
        ctx.data("adapt", "book"),
        ctx.data("citations", "citations"),
        ctx.data("origin", "origins"),
        ctx.config,
    )
    return StepResult(
        files={"related_works.json": result.to_json()},
        data={
            "related_works": result,
            "counts": {"works": len(result.works), "work_relations": len(result.relations)},
        },
    )


def units(ctx: RunContext) -> StepResult:
    from ilm_engine.enrichment.issues import make_issue
    from ilm_engine.extractors.units import (
        assemble_units,
        detect_entries,
        with_llm_facts,
        with_rule_facts,
        with_section_membership,
    )

    book, origins = ctx.data("adapt", "book"), ctx.data("origin", "origins")
    structure = ctx.data("structure", "structure")
    annotations = ctx.data("annotations", "annotations").annotations
    decision = ctx.data("genre", "genre")
    detection = detect_entries(book, origins, ctx.config)
    result, issues = assemble_units(
        book,
        detection,
        annotations,
        structure,
        ctx.config,
        genre=decision.primary or "biography",
        sub_type=decision.sub_type,
    )
    result = with_section_membership(book, with_rule_facts(book, result, origins, ctx.config), structure)
    model_outputs: dict = {}
    if ctx.llm is not None and ctx.options.get("llm", "null") != "null":
        result, llm_issues, model_outputs = with_llm_facts(
            book,
            result,
            {a.annotation_id: a for a in annotations},
            origins,
            structure,
            ctx.config,
            ctx.llm,
            verifier=ctx.options.get("verifier"),
        )
        issues += llm_issues
    else:
        issues.append(
            make_issue(
                book.book.pub_ref,
                "needs_llm",
                "info",
                "book",
                book.book.pub_ref,
                f"LLM fact extraction (entry_facts) not run for {len(result)} units: no LLM provider; "
                "only rule-based facts were extracted.",
                "units",
                details={"task": "entry_facts", "units": len(result)},
                key="entry_facts",
            )
        )
    return StepResult(
        files={"knowledge_units.json": result},
        data={
            "units": result,
            "entries": detection,
            "model_outputs": model_outputs,
            "counts": {"units": len(result), "facts": sum(len(u.facts) for u in result)},
        },
        issues=issues,
    )


def _optional(ctx: RunContext, step: str, key: str, default: object) -> object:
    result = ctx.results.get(step)
    return result.data.get(key, default) if result is not None else default


def validate(ctx: RunContext) -> StepResult:
    from ilm_engine.validation.rules import Records
    from ilm_engine.validation.validate import validate as run_validation

    book = ctx.data("adapt", "book")
    related = _optional(ctx, "related_works", "related_works", None)
    citations = _optional(ctx, "citations", "citations", None)
    internal = _optional(ctx, "citations", "internal_refs", None)
    annotations = _optional(ctx, "annotations", "annotations", None)
    structure = _optional(ctx, "structure", "structure", None)
    records = Records(
        units=list(_optional(ctx, "entities", "units", None) or _optional(ctx, "units", "units", [])),  # type: ignore[call-overload,arg-type]
        entities=list(
            _optional(ctx, "relations", "entities", None) or _optional(ctx, "entities", "entities", [])
        ),  # type: ignore[call-overload,arg-type]
        relationships=list(_optional(ctx, "relations", "relationships", [])),  # type: ignore[call-overload]
        works=list(related.works) if related else [],  # type: ignore[attr-defined]
        work_relations=list(related.relations) if related else [],  # type: ignore[attr-defined]
        others=[
            *(annotations.annotations if annotations else []),  # type: ignore[attr-defined]
            *(citations.citations if citations else []),  # type: ignore[attr-defined]
            *(internal.refs if internal else []),  # type: ignore[attr-defined]
            *(structure.sections if structure else []),  # type: ignore[attr-defined]
        ],
    )
    decision = ctx.data("genre", "genre")
    genres = [g for g in [decision.primary, *decision.secondary] if g]
    validation = run_validation(book, records, ctx.config, genres)
    return StepResult(
        files={"validation_report.json": validation.to_json()},
        data={"validation": validation, "records": validation.records},
        issues=validation.issues,
    )


def search_index(ctx: RunContext) -> StepResult:
    from ilm_engine.search.lexical import build_index

    index = build_index(
        ctx.data("adapt", "book"),
        list(_optional(ctx, "units", "units", [])),  # type: ignore[call-overload]
        list(_optional(ctx, "relations", "entities", None) or _optional(ctx, "entities", "entities", [])),  # type: ignore[call-overload,arg-type]
    )
    semantic = False
    if ctx.config.features.semantic_search:
        from ilm_engine.search.semantic import vectors

        semantic = vectors(index) is not None  # logs once and stays lexical when the model is missing
    return StepResult(
        files={"search_index.json": index},
        data={
            "search_index": index,
            "semantic": semantic,
            "counts": {"search_documents": len(index["documents"])},
        },
    )


def entities(ctx: RunContext) -> StepResult:
    from ilm_engine.extractors.entities import build_entities

    units = ctx.data("units", "units")
    result = build_entities(
        ctx.data("adapt", "book"),
        units,
        ctx.data("metadata", "metadata"),
        ctx.data("origin", "origins"),
        ctx.config,
    )
    linked = [u.model_copy(update={"subject_entity_id": result.unit_subjects.get(u.unit_id)}) for u in units]
    return StepResult(
        files={"entities.json": result.entities},
        data={
            "entities": result.entities,
            "units": linked,
            "result": result,
            "counts": {"entities": len(result.entities)},
        },
        issues=result.issues,
    )


def relations(ctx: RunContext) -> StepResult:
    from ilm_engine.extractors.relations import inferred_relations, relation_kinds, sibling_groups

    book, units = ctx.data("adapt", "book"), ctx.data("entities", "units")
    result = sibling_groups(book, units, ctx.data("entities", "entities"), ctx.config)
    result = relation_kinds(book, units, result, ctx.config)
    result = inferred_relations(book, units, result, ctx.config)
    return StepResult(
        files={"relationships.json": result.relationships},
        data={
            "relationships": result.relationships,
            "entities": result.entities,
            "groups": result.groups,
            "counts": {"relationships": len(result.relationships), "entities": len(result.entities)},
        },
        issues=result.issues,
    )


def review_queue(ctx: RunContext) -> StepResult:
    import os

    from ilm_engine.storage.json_store import write_bytes_atomic
    from ilm_engine.validation.review_html import render
    from ilm_engine.validation.review_queue import build_queue, load_decisions

    book = ctx.data("adapt", "book")
    validation = ctx.data("validate", "validation")
    records: dict[str, object] = {}
    for unit in validation.records.units:
        records[unit.unit_id] = unit
        records.update({fact.fact_id: fact for fact in unit.facts})
    records.update({e.entity_id: e for e in validation.records.entities})
    records.update({r.relation_id: r for r in validation.records.relationships})
    for item in validation.records.others:
        for attribute in ("annotation_id", "citation_id", "internal_ref_id"):
            if hasattr(item, attribute):
                records[getattr(item, attribute)] = item
        for target in getattr(item, "target_block_ids", [])[:1]:
            if getattr(item, "type", "") == "nested_footnote":
                records[target] = item  # nested-footnote issues target the footnote block

    issues = [issue for result in ctx.results.values() for issue in result.issues]
    decisions = load_decisions(ctx.store.path("review_decisions.json"))
    items = build_queue(book, validation.results, issues, records, decisions)
    stored = ctx.data("integrity_register", "stored")
    pdf = next((name for name in stored.files if name.endswith(".pdf")), None)
    href = os.path.relpath(stored.directory / pdf, ctx.store.directory) if pdf else None
    write_bytes_atomic(ctx.store.directory / "review.html", render(book, items, href).encode("utf-8"))
    return StepResult(
        files={"review_queue.json": items},
        data={"review_items": items, "counts": {"review_items": len(items)}},
    )


def store(ctx: RunContext) -> StepResult:
    from ilm_engine.pipeline.manifest import run_id
    from ilm_engine.storage.json_store import consolidate
    from ilm_engine.storage.sqlite_store import DB_NAME, SqliteStore

    book = ctx.data("adapt", "book")
    validation = ctx.data("validate", "validation")
    records = validation.records
    related = ctx.data("related_works", "related_works")
    enrichment = consolidate(
        book=book,
        run_id=run_id(ctx),
        report=ctx.data("document_analysis", "report"),
        metadata=ctx.data("metadata", "metadata"),
        genre_primary=ctx.data("genre", "genre_primary"),
        genre_secondary=ctx.data("genre", "genre_secondary"),
        structure=ctx.data("structure", "structure"),
        origin_spans=ctx.data("origin", "origin_map").spans,
        annotations=ctx.data("annotations", "annotations").annotations,
        internal_refs=ctx.data("citations", "internal_refs").refs,
        citations=ctx.data("citations", "citations").citations,
        works=related.works,
        work_relations=related.relations,
        units=records.units,
        entities=records.entities,
        relationships=records.relationships,
        validation=validation.results,
        issues=[issue for result in ctx.results.values() for issue in result.issues],
        review_items=ctx.data("review_queue", "review_items"),
    )
    database = SqliteStore(ctx.store.directory / DB_NAME)
    database.path.unlink(missing_ok=True)  # rebuilt from this run's records (idempotent upserts within)
    payload = enrichment.model_dump(mode="json", by_alias=True)
    payload["review_items"] = [
        item.model_dump(mode="json") for item in ctx.data("review_queue", "review_items")
    ]
    counts = database.load(payload, book=book, origins=ctx.data("origin", "origins"))
    return StepResult(data={"enrichment": enrichment, "db_counts": counts})


def export(ctx: RunContext) -> StepResult:
    from ilm_engine.storage.derived import edges_from_records, write_graph

    enrichment = ctx.data("store", "enrichment")
    write_graph(
        ctx.store.directory,
        ctx.data("adapt", "book"),
        enrichment.entities,
        enrichment.works,
        edges_from_records(enrichment.relationships, enrichment.work_relations),
    )
    return StepResult(files={"enrichment.json": enrichment}, data={"counts": dict(enrichment.stats)})


def integrity_verify(ctx: RunContext) -> StepResult:
    from ilm_engine.integrity import store as original_store
    from ilm_engine.integrity.verify import IntegrityError, check_anchors, originals_unchanged

    book = ctx.data("adapt", "book")
    stored = ctx.data("integrity_register", "stored")
    store_root = ctx.options.get("store_root", original_store.DEFAULT_STORE_ROOT)
    problems = originals_unchanged(ctx.inputs, stored, store_root)
    enrichment = ctx.data("store", "enrichment").model_dump(mode="json", by_alias=True)
    checked, anchor_problems = check_anchors(book, enrichment, "enrichment.json")
    problems += [str(problem) for problem in anchor_problems]
    if problems:
        raise IntegrityError(problems)
    return StepResult(
        data={
            "integrity": {
                "originals_unchanged": True,
                "anchors_checked": checked,
                "stale": 0,
                "canonical_content_hash": book.canonical_content_hash,
                "source_declared_hash_verified": book.source.source_declared_hash_verified,
            }
        }
    )
