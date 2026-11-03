"""LLM response cache (ADR-006, ADR-011).

Responses are stored as JSON files under `.cache/llm/<key>.json`, where the key covers everything that
determines the answer: provider, model, task, prompt version and the canonical input. With temperature
0 this makes reruns repeatable and free.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ilm_engine.integrity.hashing import canonical_json

DEFAULT_CACHE_DIR = Path(".cache") / "llm"


def request_key(model: str, task: str, prompt_version: str, input: Any) -> str:
    """Provider-independent key of a request (also names recorded fixtures)."""
    payload = {"model": model, "task": task, "prompt_version": prompt_version, "input": input}
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def cache_key(provider: str, model: str, task: str, prompt_version: str, input: Any) -> str:
    """Cache key: sha256 over provider + model + task + prompt version + canonical input."""
    payload = {"provider": provider, "request": request_key(model, task, prompt_version, input)}
    return hashlib.sha256(canonical_json(payload)).hexdigest()


class ResponseCache:
    def __init__(self, directory: str | Path = DEFAULT_CACHE_DIR) -> None:
        self.directory = Path(directory)

    def _path(self, key: str) -> Path:
        if not key or not all(char in "0123456789abcdef" for char in key):
            raise ValueError(f"invalid cache key {key!r}")
        return self.directory / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None  # a corrupt entry is treated as a miss and overwritten on the next put

    def put(self, key: str, record: dict[str, Any]) -> None:
        """Write atomically, so a crash never leaves a half-written entry."""
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False, sort_keys=True, indent=2)
        os.replace(temporary, path)
