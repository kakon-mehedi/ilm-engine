"""Optional semantic search: BGE-M3 via sentence-transformers (`semantic` extra); Qdrant in production.

Off unless `features.semantic_search` is on and the library and model are available; otherwise the
pipeline logs once and uses lexical search only. Vectors of the indexed documents are cached as
`.cache/vectors/<pub_ref>.npy`. Hybrid score = 0.5 × normalized BM25 + 0.5 × cosine similarity.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from ilm_engine.log import get_logger
from ilm_engine.search.lexical import Hit, search

log = get_logger("search.semantic")

MODEL_NAME = "BAAI/bge-m3"
DEFAULT_CACHE = Path(".cache") / "vectors"
LEXICAL_WEIGHT = 0.5


@lru_cache(maxsize=1)
def _model(name: str = MODEL_NAME) -> Any | None:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        log.info("semantic search off: sentence-transformers is not installed (the 'semantic' extra)")
        return None
    try:
        return SentenceTransformer(name)
    except Exception as exc:  # model download or load failure
        log.warning("semantic search off: model unavailable", extra={"model": name, "error": str(exc)})
        return None


def is_available(enabled: bool = True) -> bool:
    return enabled and _model() is not None


def _document_texts(index: dict[str, Any]) -> list[str]:
    return [
        (doc.get("title") or "") + " " + ((doc.get("anchor") or {}).get("quote") or "")
        for doc in index["documents"]
    ]


def vectors(index: dict[str, Any], cache_dir: Path = DEFAULT_CACHE) -> Any | None:
    """Normalized document embeddings (cached per book), or None when semantic search is unavailable."""
    model = _model()
    if model is None:
        return None
    import numpy as np

    path = cache_dir / f"{index['pub_ref']}.npy"
    if path.is_file():
        cached = np.load(path)
        if cached.shape[0] == len(index["documents"]):
            return cached
    embedded = model.encode(_document_texts(index), normalize_embeddings=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, embedded)
    return embedded


def hybrid_search(
    index: dict[str, Any], query: str, limit: int = 10, cache_dir: Path = DEFAULT_CACHE
) -> list[Hit]:
    """Hybrid BM25 + cosine ranking; falls back to lexical search when the model is unavailable."""
    document_vectors = vectors(index, cache_dir)
    if document_vectors is None:
        return search(index, query, limit)
    lexical = {hit.doc_id: hit.score for hit in search(index, query, limit=len(index["documents"]))}
    top = max(lexical.values(), default=1.0) or 1.0
    query_vector = _model().encode([query], normalize_embeddings=True)[0]  # type: ignore[union-attr]
    cosine = document_vectors @ query_vector
    scored = []
    for position, doc in enumerate(index["documents"]):
        score = LEXICAL_WEIGHT * lexical.get(doc["doc_id"], 0.0) / top + (1 - LEXICAL_WEIGHT) * float(
            cosine[position]
        )
        scored.append((round(score, 6), position))
    scored.sort(key=lambda item: (-item[0], item[1]))
    docs = index["documents"]
    return [Hit(docs[i]["doc_id"], docs[i]["kind"], score, docs[i]["anchor"]) for score, i in scored[:limit]]
