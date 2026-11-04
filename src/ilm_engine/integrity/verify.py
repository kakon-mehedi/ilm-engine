"""Integrity invariants (ADR-017, step `integrity_verify` and `ilm-engine verify`).

1. Originals unchanged: the input files still hash to what was registered, and the read-only store
   verifies.
2. Every anchor in the outputs points at its quote: `block.text[start:end] == quote` (unless the quote
   is marked truncated) and `block_hash` equals the current block's hash.
A failure names the file and the JSON path of the anchor; the pipeline run fails.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ilm_engine.canonical.models import CanonicalBook
from ilm_engine.integrity import store as original_store
from ilm_engine.integrity.hashing import file_sha256

ANCHOR_KEYS = {"block_id", "start", "end", "quote", "block_hash"}


class IntegrityError(RuntimeError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__(
            "; ".join(problems[:5]) + (f" (+{len(problems) - 5} more)" if len(problems) > 5 else "")
        )
        self.problems = problems


@dataclass(frozen=True)
class AnchorProblem:
    path: str
    block_id: str
    start: int
    end: int
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: anchor {self.block_id}[{self.start}:{self.end}] {self.reason}"


def iter_anchors(data: Any, path: str = "$") -> Iterator[tuple[str, dict[str, Any]]]:
    """Every anchor-shaped object in a JSON document, with its JSON path."""
    if isinstance(data, dict):
        if ANCHOR_KEYS <= set(data):
            yield path, data
        for key, value in data.items():
            yield from iter_anchors(value, f"{path}.{key}")
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from iter_anchors(value, f"{path}[{index}]")


def check_anchors(book: CanonicalBook, data: Any, label: str = "$") -> tuple[int, list[AnchorProblem]]:
    """(anchors checked, problems) for every anchor in `data` (JSON-like)."""
    checked, problems = 0, []
    for path, anchor in iter_anchors(data, label):
        checked += 1
        block = book.blocks.get(anchor["block_id"])
        start, end = anchor["start"], anchor["end"]
        if block is None:
            problems.append(AnchorProblem(path, anchor["block_id"], start, end, "points to a missing block"))
        elif anchor["block_hash"] != block.block_hash:
            problems.append(AnchorProblem(path, block.block_id, start, end, "has a stale block_hash"))
        elif not anchor.get("quote_truncated") and block.text[start:end] != anchor["quote"]:
            problems.append(
                AnchorProblem(path, block.block_id, start, end, f"quote {anchor['quote']!r} is not the text")
            )
        elif anchor.get("quote_truncated") and not block.text[start:end].startswith(anchor["quote"]):
            problems.append(
                AnchorProblem(path, block.block_id, start, end, "truncated quote is not the text")
            )
    return checked, problems


def originals_unchanged(inputs: dict[str, Path], stored: Any, store_root: Path) -> list[str]:
    """Problems with the originals: an input file changed since ingest, or the store fails verification."""
    problems = []
    for path in inputs.values():
        expected = stored.files.get(path.name)
        if expected is None or not path.is_file() or file_sha256(path) != expected.sha256:
            problems.append(f"input {path} changed since it was registered")
    if not original_store.verify(stored.pub_ref, store_root):
        problems.append(f"original store for {stored.pub_ref} failed verification")
    return problems
