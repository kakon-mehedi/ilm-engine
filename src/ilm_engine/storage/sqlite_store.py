"""SQLite enrichment database `enrichment.db` (03-data-contracts §19; PostgreSQL in production, ADR-005).

`load` takes the consolidated enrichment (the §18 shape, as models or plain JSON) plus the canonical
blocks and upserts every record by its ID, so loading the same run twice leaves the same rows.
Anchors of every record are stored in `anchor` (owner kind + id); block text is never stored.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.storage.json_store import ensure_writable, to_jsonable

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"
DB_NAME = "enrichment.db"


def _json(value: Any) -> str:
    return json.dumps(to_jsonable(value), ensure_ascii=False, sort_keys=True)


def _anchors(record: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Anchors directly held by a record (its own text spans, evidence, mentions, marker)."""
    found: list[Mapping[str, Any]] = []
    for key in ("anchor", "marker_anchor"):
        if isinstance(record.get(key), Mapping):
            found.append(record[key])
    for key in ("anchors", "evidence", "mentions"):
        found.extend(item for item in record.get(key) or [] if isinstance(item, Mapping))
    return found


class SqliteStore:
    def __init__(self, path: str | Path) -> None:
        self.path = ensure_writable(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        return connection

    def load(
        self,
        enrichment: Any,
        book: CanonicalBook | None = None,
        origins: Mapping[str, str] | None = None,
        manifest: Any | None = None,
    ) -> dict[str, int]:
        """Upsert the enrichment (and the book's blocks); returns row counts per table."""
        data = to_jsonable(enrichment)
        pub_ref = data["pub_ref"]
        with self.connect() as db:
            if book is not None:
                self._book(db, book, data.get("source", {}), origins or {})
            sections = (data.get("structure") or {}).get("sections", [])
            for section in sections:
                db.execute(
                    "INSERT OR REPLACE INTO section VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        section["section_id"],
                        pub_ref,
                        section["parent_id"],
                        section["level"],
                        section["title"],
                        section["heading_block_id"],
                        section["start_block_id"],
                        section["end_block_id"],
                        section["origin"],
                        _json(section),
                    ),
                )
            for annotation in data.get("annotations", []):
                self._annotation(db, pub_ref, annotation)
            for ref in data.get("internal_refs", []):
                db.execute(
                    "INSERT OR REPLACE INTO annotation VALUES (?,?,?,?,?,?,?,?)",
                    (
                        ref["internal_ref_id"],
                        pub_ref,
                        "internal_ref",
                        ref["anchor"]["block_id"],
                        _json([ref["target_unit_id"]] if ref.get("target_unit_id") else []),
                        "rule",
                        ref["status"],
                        _json(ref),
                    ),
                )
                self._replace_anchors(db, "internal_ref", ref["internal_ref_id"], _anchors(ref))
            for citation in data.get("citations", []):
                db.execute(
                    "INSERT OR REPLACE INTO citation VALUES (?,?,?,?,?)",
                    (
                        citation["citation_id"],
                        pub_ref,
                        citation["title_normalized"],
                        citation["work_id"],
                        _json(citation),
                    ),
                )
                self._replace_anchors(db, "citation", citation["citation_id"], _anchors(citation))
            for work in data.get("works", []):
                db.execute(
                    "INSERT OR REPLACE INTO work VALUES (?,?,?,?,?)",
                    (work["work_id"], work["title"], work["title_normalized"], work["status"], _json(work)),
                )
            for relation in data.get("work_relations", []):
                db.execute(
                    "INSERT OR REPLACE INTO work_relation VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        relation["relation_id"],
                        relation["type"],
                        relation["subject_work_id"],
                        relation["object_work_id"],
                        relation["origin"],
                        relation["assertion"],
                        relation["confidence"],
                        relation["review_status"],
                        _json(relation),
                    ),
                )
                self._replace_anchors(db, "work_relation", relation["relation_id"], _anchors(relation))
            for unit in data.get("knowledge_units", []):
                self._unit(db, pub_ref, unit)
            for entity in data.get("entities", []):
                db.execute(
                    "INSERT OR REPLACE INTO entity VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        entity["entity_id"],
                        entity["entity_type"],
                        entity["canonical_name"],
                        entity["canonical_name_normalized"],
                        entity["gender"],
                        entity["disambiguation"],
                        entity["confidence"],
                        entity["review_status"],
                        _json(entity),
                    ),
                )
                self._replace_anchors(db, "entity", entity["entity_id"], _anchors(entity))
            for relation in data.get("relationships", []):
                db.execute(
                    "INSERT OR REPLACE INTO relationship VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        relation["relation_id"],
                        relation["type"],
                        relation["subject_entity_id"],
                        relation["object_entity_id"],
                        _json(relation["attrs"]),
                        relation["origin"],
                        relation["assertion"],
                        relation["confidence"],
                        relation["review_status"],
                        _json(relation["provenance"]),
                    ),
                )
                self._replace_anchors(db, "relationship", relation["relation_id"], _anchors(relation))
            for issue in data.get("issues", []):
                db.execute(
                    "INSERT OR REPLACE INTO issue VALUES (?,?,?,?,?,?)",
                    (
                        issue["issue_id"],
                        issue["code"],
                        issue["severity"],
                        issue["target_kind"],
                        issue["target_id"],
                        _json(issue),
                    ),
                )
            for result in data.get("validation", []):
                db.execute(
                    "INSERT OR REPLACE INTO validation VALUES (?,?,?,?,?)",
                    (
                        result["target_kind"],
                        result["target_id"],
                        result["confidence"],
                        result["decision"],
                        _json(result),
                    ),
                )
            for item in data.get("review_items", []):
                self.upsert_review_item(db, item)
            if manifest is not None:
                manifest_data = to_jsonable(manifest)
                db.execute(
                    "INSERT OR REPLACE INTO run VALUES (?,?,?)",
                    (manifest_data["run_id"], manifest_data["pub_ref"], _json(manifest_data)),
                )
        return self.counts()

    @staticmethod
    def upsert_review_item(db: sqlite3.Connection, item: Any) -> None:
        item = to_jsonable(item)
        db.execute(
            "INSERT OR REPLACE INTO review_item VALUES (?,?,?,?,?,?,?)",
            (
                item["review_id"],
                item["target_kind"],
                item["target_id"],
                item["priority"],
                item["required_role"],
                item["status"],
                _json(item),
            ),
        )

    def _book(
        self,
        db: sqlite3.Connection,
        book: CanonicalBook,
        source: Mapping[str, Any],
        origins: Mapping[str, str],
    ) -> None:
        pub_ref = book.book.pub_ref
        db.execute(
            "INSERT OR REPLACE INTO book VALUES (?,?,?,?,?,?,?,?,?)",
            (
                pub_ref,
                book.book.pub_id,
                book.book.revision,
                book.source.source_code,
                book.source.schema_version,
                source.get("adapter") or f"{book.source.adapter_id}@{book.source.adapter_version}",
                book.canonical_content_hash,
                book.source.source_declared_hash,
                int(book.source.source_declared_hash_verified),
            ),
        )
        scan_pages = {(page.volume, page.n): page.scan_page for page in book.pages}
        db.executemany(
            "INSERT OR REPLACE INTO block VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    block.block_id,
                    pub_ref,
                    block.order,
                    block.page,
                    scan_pages.get((block.volume, block.page)),
                    block.kind,
                    origins.get(block.block_id),
                    block.block_hash,
                )
                for block in book.blocks_in_order()
            ],
        )

    def _annotation(self, db: sqlite3.Connection, pub_ref: str, annotation: Mapping[str, Any]) -> None:
        db.execute(
            "INSERT OR REPLACE INTO annotation VALUES (?,?,?,?,?,?,?,?)",
            (
                annotation["annotation_id"],
                pub_ref,
                annotation["type"],
                annotation["source_block_id"],
                _json(annotation["target_block_ids"]),
                annotation["link_method"],
                annotation["status"],
                _json(annotation),
            ),
        )
        self._replace_anchors(db, "annotation", annotation["annotation_id"], _anchors(annotation))

    def _unit(self, db: sqlite3.Connection, pub_ref: str, unit: Mapping[str, Any]) -> None:
        db.execute(
            "INSERT OR REPLACE INTO knowledge_unit VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                unit["unit_id"],
                pub_ref,
                unit["genre"],
                unit["unit_type"],
                unit["entry_no"],
                unit["section_id"],
                unit["subject_entity_id"],
                unit["origin"],
                unit["confidence"],
                unit["review_status"],
                _json(unit["payload"]),
            ),
        )
        self._replace_anchors(db, "unit", unit["unit_id"], _anchors(unit))
        db.execute("DELETE FROM fact WHERE unit_id = ?", (unit["unit_id"],))
        for fact in unit.get("facts", []):
            db.execute(
                "INSERT OR REPLACE INTO fact VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    fact["fact_id"],
                    unit["unit_id"],
                    fact["predicate"],
                    _json(fact["object"]),
                    fact["origin"],
                    fact["assertion"],
                    fact["confidence"],
                    _json(fact.get("sensitive", [])),
                    fact["review_status"],
                    _json(fact["provenance"]),
                ),
            )
            self._replace_anchors(db, "fact", fact["fact_id"], _anchors(fact))

    @staticmethod
    def _replace_anchors(
        db: sqlite3.Connection, owner_kind: str, owner_id: str, anchors: Iterable[Mapping[str, Any]]
    ) -> None:
        db.execute("DELETE FROM anchor WHERE owner_kind = ? AND owner_id = ?", (owner_kind, owner_id))
        db.executemany(
            "INSERT OR REPLACE INTO anchor VALUES (?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    f"{owner_kind}:{owner_id}#a{index}",
                    owner_kind,
                    owner_id,
                    anchor["pub_ref"],
                    anchor["block_id"],
                    anchor["start"],
                    anchor["end"],
                    anchor["quote"],
                    anchor["block_hash"],
                    anchor.get("status", "valid"),
                )
                for index, anchor in enumerate(anchors)
            ],
        )

    def counts(self) -> dict[str, int]:
        with self.connect() as db:
            tables = [
                row[0]
                for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            ]
            return {table: db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] for table in tables}

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with self.connect() as db:
            return db.execute(sql, params).fetchall()
