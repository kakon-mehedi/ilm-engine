"""JSON Schema export of the contract models (03-data-contracts §21).

`ilm-engine schema export --out schemas/` writes one `<Model>.json` per top-level model. The exported
schemas are committed; a test fails if a model changes without re-exporting, which keeps downstream
consumers' contract explicit.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.enrichment import models as enrichment
from ilm_engine.storage.json_store import write_bytes_atomic

TOP_LEVEL_MODELS: tuple[type[BaseModel], ...] = (
    CanonicalBook,
    enrichment.Anchor,
    enrichment.Issue,
    enrichment.DocumentReport,
    enrichment.Section,
    enrichment.OriginSpan,
    enrichment.BookMetadata,
    enrichment.Annotation,
    enrichment.Citation,
    enrichment.InternalRef,
    enrichment.Work,
    enrichment.WorkRelation,
    enrichment.KnowledgeUnit,
    enrichment.Fact,
    enrichment.Entity,
    enrichment.Relationship,
    enrichment.ValidationResult,
    enrichment.ReviewItem,
    enrichment.ReviewDecision,
    enrichment.RunManifest,
    enrichment.Enrichment,
)


def _models() -> dict[str, type[BaseModel]]:
    from ilm_engine.extractors.genres import registry

    named = {model.__name__: model for model in TOP_LEVEL_MODELS}
    named.update({f"genre_{genre}": plugin.unit_schema for genre, plugin in registry().items()})
    return named


def schemas() -> dict[str, bytes]:
    """File name → canonical JSON bytes of each model's JSON Schema (serialization mode, by alias),
    plus one schema per genre payload (`genre_<genre>.json`)."""
    return {
        f"{name}.json": (
            json.dumps(
                model.model_json_schema(by_alias=True, mode="serialization"),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n"
        ).encode("utf-8")
        for name, model in _models().items()
    }


def export(out: Path) -> list[Path]:
    return [write_bytes_atomic(out / name, data) for name, data in sorted(schemas().items())]
