"""JSON enrichment store: the per-run output files of DECISIONS §10 under `output/<pub_ref>/`.

Files are canonical JSON (sorted keys, UTF-8, indent 2, trailing newline), so the same objects always
give byte-identical files. Writes are atomic (temporary file + rename). The store refuses any path under
the read-only inputs (`data/`, `store/originals/`).
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[3]
PROTECTED = (Path("data"), Path("store") / "originals")

OUTPUT_FILES = frozenset(
    {
        "run_manifest.json",
        "document_report.json",
        "metadata.json",
        "structure.json",
        "origin_map.json",
        "annotations.json",
        "citations.json",
        "related_works.json",
        "knowledge_units.json",
        "entities.json",
        "relationships.json",
        "search_index.json",
        "validation_report.json",
        "review_queue.json",
        "enrichment.json",
        "eval_report.json",
        "review_decisions.json",
    }
)


class ProtectedPathError(PermissionError):
    """A write would land inside the read-only originals."""


def to_jsonable(obj: Any) -> Any:
    """Pydantic models (by contract alias), lists, tuples and dicts → plain JSON values."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json", by_alias=True)
    if isinstance(obj, dict):
        return {str(key): to_jsonable(value) for key, value in obj.items()}
    if isinstance(obj, list | tuple):
        return [to_jsonable(item) for item in obj]
    return obj


def dumps(obj: Any) -> bytes:
    """Canonical JSON bytes of `obj`."""
    text = json.dumps(to_jsonable(obj), sort_keys=True, ensure_ascii=False, indent=2)
    return (text + "\n").encode("utf-8")


def ensure_writable(path: str | Path, protected_roots: Iterable[Path] | None = None) -> Path:
    """Resolve `path`, raising `ProtectedPathError` if it is inside a protected input folder."""
    resolved = Path(path).resolve()
    roots = list(protected_roots) if protected_roots is not None else list(PROTECTED)
    for root in roots:
        for base in {Path.cwd(), REPO_ROOT}:
            protected = (root if root.is_absolute() else base / root).resolve()
            if resolved == protected or protected in resolved.parents:
                raise ProtectedPathError(f"refusing to write {resolved}: it is inside read-only {protected}")
    return resolved


def write_bytes_atomic(path: str | Path, data: bytes) -> Path:
    target = ensure_writable(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=target.parent, prefix=f".{target.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return target


class JsonStore:
    """Output files of one book run: `<out_root>/<pub_ref>/<name>`."""

    def __init__(self, pub_ref: str, out_root: str | Path = "output") -> None:
        if not pub_ref or "/" in pub_ref or pub_ref.startswith("."):
            raise ValueError(f"invalid pub_ref for an output folder: {pub_ref!r}")
        self.pub_ref = pub_ref
        self.directory = ensure_writable(Path(out_root) / pub_ref)

    def path(self, name: str) -> Path:
        if name not in OUTPUT_FILES:
            raise ValueError(f"{name!r} is not an output file of DECISIONS §10")
        return self.directory / name

    def write(self, name: str, obj: Any) -> Path:
        """Write `obj` as canonical JSON to the output file `name`."""
        return write_bytes_atomic(self.path(name), dumps(obj))

    def read(self, name: str) -> Any:
        return json.loads(self.path(name).read_text(encoding="utf-8"))

    def exists(self, name: str) -> bool:
        return self.path(name).is_file()

    def files(self) -> list[Path]:
        """Existing output files, sorted by name."""
        return sorted(
            path for path in self.directory.glob("*") if path.is_file() and not path.name.startswith(".")
        )


# --- Consolidated enrichment.json (T-112) ---------------------------------------------------------------


def _by(items: list[Any], attribute: str) -> list[Any]:
    return sorted(items, key=lambda item: getattr(item, attribute))


def consolidate(
    *,
    book: Any,
    run_id: str,
    report: Any,
    metadata: Any,
    genre_primary: Any,
    genre_secondary: list[Any],
    structure: Any,
    origin_spans: list[Any],
    annotations: list[Any],
    internal_refs: list[Any],
    citations: list[Any],
    works: list[Any],
    work_relations: list[Any],
    units: list[Any],
    entities: list[Any],
    relationships: list[Any],
    validation: list[Any],
    issues: list[Any],
    review_items: list[Any],
) -> Any:
    """The `Enrichment` record (03-data-contracts §18): every output in one object, lists sorted by ID.

    Review decisions already applied to the queue are reflected in the targets' `review_status`.
    """
    from ilm_engine.enrichment.models import Enrichment, EnrichmentSource, Structure

    decided = {item.target_id: item.status for item in review_items if item.status != "pending_review"}

    def reviewed(record: Any, identifier: str) -> Any:
        return (
            record.model_copy(update={"review_status": decided[identifier]})
            if identifier in decided
            else record
        )

    units = [
        reviewed(unit, unit.unit_id).model_copy(
            update={"facts": [reviewed(f, f.fact_id) for f in unit.facts]}
        )
        for unit in units
    ]
    unique_issues = {issue.issue_id: issue for issue in issues}
    stats = {
        "blocks": len(book.blocks),
        "pages": len(book.pages),
        "sections": len(structure.sections),
        "units": len(units),
        "facts": sum(len(unit.facts) for unit in units),
        "annotations": len(annotations),
        "citations": len(citations),
        "entities": len(entities),
        "relationships": len(relationships),
        "review_items": len(review_items),
        "issues": len(unique_issues),
    }
    return Enrichment(
        pub_ref=book.book.pub_ref,
        run_id=run_id,
        source=EnrichmentSource(
            source_code=book.source.source_code,
            schema_version=book.source.schema_version,
            adapter=f"{book.source.adapter_id}@{book.source.adapter_version}",
            canonical_content_hash=book.canonical_content_hash,
            source_declared_hash=book.source.source_declared_hash,
            source_declared_hash_verified=book.source.source_declared_hash_verified,
        ),
        document_report=report,
        metadata=metadata.model_copy(
            update={"genre_primary": genre_primary, "genre_secondary": genre_secondary}
        ),
        structure=Structure(
            root_section_id=structure.root_section_id, sections=_by(structure.sections, "section_id")
        ),
        origin_map=origin_spans,
        annotations=_by(annotations, "annotation_id"),
        internal_refs=_by(internal_refs, "internal_ref_id"),
        citations=_by(citations, "citation_id"),
        works=_by(works, "work_id"),
        work_relations=_by(work_relations, "relation_id"),
        knowledge_units=_by(units, "unit_id"),
        entities=_by([reviewed(e, e.entity_id) for e in entities], "entity_id"),
        relationships=_by([reviewed(r, r.relation_id) for r in relationships], "relation_id"),
        validation=sorted(validation, key=lambda v: (v.target_kind, v.target_id)),
        issues=sorted(unique_issues.values(), key=lambda issue: issue.issue_id),
        review_queue_ids=[item.review_id for item in review_items],
        stats=stats,
    )
