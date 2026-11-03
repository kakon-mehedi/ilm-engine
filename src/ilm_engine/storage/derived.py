"""Rebuild derived outputs (`search_index.json`, `graph.html`, `graph.cypher`) from `enrichment.db`
and the read-only original store (ADR-005: derived stores are always rebuildable from the source of
truth; block text never lives in the database)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from ilm_engine.adapters.registry import resolve
from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.enrichment.models import Anchor, Entity, RunManifest, Work
from ilm_engine.integrity import store as original_store
from ilm_engine.search.lexical import build_index
from ilm_engine.storage.graph_export import Edge, build_graph, edges_from_records, render_cypher, render_html
from ilm_engine.storage.json_store import JsonStore, write_bytes_atomic
from ilm_engine.storage.sqlite_store import DB_NAME, SqliteStore


def write_graph(
    out_dir: Path,
    book: CanonicalBook,
    entities: list[Any],
    works: list[Any],
    edges: tuple[list[Edge], list[Edge]],
) -> list[Path]:
    graph = build_graph(entities, works, *edges)
    title = book.metadata.title_as_source or book.book.pub_ref
    return [
        write_bytes_atomic(out_dir / "graph.html", render_html(graph, title).encode("utf-8")),
        write_bytes_atomic(out_dir / "graph.cypher", render_cypher(graph).encode("utf-8")),
    ]


def rebuild_derived(out_dir: Path, store_root: Path = original_store.DEFAULT_STORE_ROOT) -> list[Path]:
    manifest = RunManifest.model_validate_json((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    stored = original_store.load(manifest.pub_ref, store_root)
    source = next(name for name in stored.files if name.endswith(".json"))
    pdf = next((name for name in stored.files if name.endswith(".pdf")), None)
    raw = json.loads(stored.path(source).read_text(encoding="utf-8"))
    book = resolve(raw).to_canonical(raw, stored.path(pdf) if pdf else None)

    db = SqliteStore(out_dir / DB_NAME)
    pages = {row[0]: (row[1], row[2]) for row in db.query("SELECT block_id, page, scan_page FROM block")}
    anchors: dict[str, list[Anchor]] = {}
    for owner, block_id, start, end, quote, block_hash, status in db.query(
        'SELECT owner_id, block_id, start, "end", quote, block_hash, status FROM anchor '
        "WHERE owner_kind = 'unit' "
        "ORDER BY owner_id, CAST(substr(anchor_id, instr(anchor_id, '#a') + 2) AS INTEGER)"
    ):
        page, scan_page = pages[block_id]
        anchors.setdefault(owner, []).append(
            Anchor(
                pub_ref=manifest.pub_ref,
                page=page,
                scan_page=scan_page,
                block_id=block_id,
                start=start,
                end=end,
                quote=quote,
                block_hash=block_hash,
                status=status,
            )
        )
    units = [
        SimpleNamespace(unit_id=unit_id, payload=json.loads(payload), anchors=anchors.get(unit_id, []))
        for unit_id, payload in db.query("SELECT unit_id, payload FROM knowledge_unit")
    ]
    entities = [Entity.model_validate_json(data) for (data,) in db.query("SELECT data FROM entity")]
    works = [Work.model_validate_json(data) for (data,) in db.query("SELECT data FROM work")]
    people = [
        Edge(subject, obj, type_, assertion, json.loads(attrs).get("kind"))
        for type_, subject, obj, attrs, assertion in db.query(
            "SELECT type, subject_entity_id, object_entity_id, attrs, assertion FROM relationship"
        )
    ]
    work_edges = [
        Edge(subject, obj, type_, assertion)
        for type_, subject, obj, assertion in db.query(
            "SELECT type, subject_work_id, object_work_id, assertion FROM work_relation"
        )
    ]
    index = JsonStore(book.book.pub_ref, out_dir.parent).write(
        "search_index.json", build_index(book, units, entities)
    )
    return [index, *write_graph(out_dir, book, entities, works, (people, work_edges))]


__all__ = ["edges_from_records", "rebuild_derived", "write_graph"]
