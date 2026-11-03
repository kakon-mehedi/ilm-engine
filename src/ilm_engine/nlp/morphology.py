"""Optional morphological analysis (lemma, root, part of speech) via CAMeL Tools.

The MVP runs without CAMeL Tools: unless `features.camel_tools` is on and the `nlp` extra (with its
morphology database) is installed, `analyze` returns `[]` and logs that once. Callers treat an empty
analysis as "no morphology available", never as an error.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, TypedDict

from ilm_engine.log import get_logger

log = get_logger("nlp.morphology")


class Analysis(TypedDict):
    lemma: str | None
    root: str | None
    pos: str | None


class _Backend:
    def __init__(self, analyzer: Any | None) -> None:
        self.analyzer = analyzer

    def analyze(self, word: str) -> list[Analysis]:
        if self.analyzer is None or not word.strip():
            return []
        seen: set[tuple[str | None, str | None, str | None]] = set()
        results: list[Analysis] = []
        for item in self.analyzer.analyze(word.strip()):
            key = (item.get("lex"), item.get("root"), item.get("pos"))
            if key not in seen:
                seen.add(key)
                results.append(Analysis(lemma=key[0], root=key[1], pos=key[2]))
        return results


@lru_cache(maxsize=2)
def _backend(enabled: bool) -> _Backend:
    if not enabled:
        log.info("morphology disabled (features.camel_tools is false); analyze() returns []")
        return _Backend(None)
    try:
        from camel_tools.morphology.analyzer import Analyzer
        from camel_tools.morphology.database import MorphologyDB
    except ImportError:
        log.warning("camel-tools is not installed (install the 'nlp' extra); analyze() returns []")
        return _Backend(None)
    try:
        return _Backend(Analyzer(MorphologyDB.builtin_db()))
    except Exception as exc:  # missing morphology database download
        log.warning(
            "CAMeL Tools morphology database unavailable; analyze() returns []", extra={"error": str(exc)}
        )
        return _Backend(None)


def analyze(word: str, enabled: bool = False) -> list[Analysis]:
    """Distinct `{lemma, root, pos}` analyses of `word`; `[]` when morphology is unavailable."""
    return _backend(enabled).analyze(word)


def is_available(enabled: bool = True) -> bool:
    return _backend(enabled).analyzer is not None


def roots_and_lemmas(words: list[str], enabled: bool = False) -> tuple[list[str], list[str]]:
    """Sorted distinct roots and lemmas of `words`, for search index entries (T-120)."""
    roots: set[str] = set()
    lemmas: set[str] = set()
    for word in words:
        for item in analyze(word, enabled):
            if item["root"]:
                roots.add(item["root"])
            if item["lemma"]:
                lemmas.add(item["lemma"])
    return sorted(roots), sorted(lemmas)
